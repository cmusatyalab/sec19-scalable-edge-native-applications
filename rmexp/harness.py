#! /usr/bin/env python
from collections import defaultdict
import docker
import fire
import importlib
import logging
import logzero
from logzero import logger
import math
import multiprocessing as mp
import numpy as np
import operator
import os
import pandas as pd
import subprocess
import threading
import time
import uuid
import yaml

import rmexp.feed
from rmexp import schema
from rmexp.schedule import Allocator, AppUtil, ScipySolver

DOCKER_IMAGE = 'res'
CGROUP_INFO = {
    'name': '/rmexp'
}
GiB = 2.**30

# logzero.loglevel(logging.INFO)

def start_worker(app, num, docker_run_kwargs):
    omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS

    cli = docker.from_env()

    container_name = 'rmexp-mc-{}-{}'.format(app, str(uuid.uuid4())[:8])

    bash_cmd = ". .envrc && OMP_NUM_THREADS={} python rmexp/serve.py start --num {} \
                --broker-type {} --broker-uri {} --app {} " \
        .format(omp_num_threads, num, os.getenv('BROKER_TYPE'), os.getenv('WORKER_BROKER_URI'), app)
    logger.debug(bash_cmd)

    try:
        logger.info('Starting workers: {}x {} @ {}'.format(
            num, app, container_name))
        cli.containers.run(
            DOCKER_IMAGE,
            ['/bin/bash', '-i', '-c', bash_cmd],
            cgroup_parent=CGROUP_INFO['name'],
            name=container_name,
            auto_remove=True,
            stderr=False,
            **docker_run_kwargs
        )
    except:
        raise


def start_feed(app, video_uri, tokens_cap, exp='', client_id=0):
    logger.info('Starting client %d %s @ %s' % (client_id, app, video_uri))

    try:
        rmexp.feed.start_single_feed_token(
            video_uri,
            app,
            os.getenv('BROKER_TYPE'),
            os.getenv('CLIENT_BROKER_URI'),
            tokens_cap=tokens_cap,
            loop=True,
            exp=exp,
            client_id=client_id
        )
    except ValueError:
        logger.info("%s finished" % video_uri)


def admission_control(app, cpu, memory):
    # solely based on cpu now
    omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS
    return int(math.ceil(cpu / float(omp_num_threads)))


def run(run_config, component, exp='', dry_run=False, **kwargs):
    """[summary]

    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
        exp {string} -- if not empty, will write latency to DB
        component -- 'client' or 'server'
        **kwargs -- override values in run_config
    """
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config, 'r'))
    run_config.update(kwargs)
    
    component = component.lower()
    assert component in ['client', 'server'], 'Component needs to be either client or server'

    # retrieve cgroup info
    global CGROUP_INFO
    cg_name = run_config.get('cgroup', CGROUP_INFO['name'])
    cg_cpus = float(len(open('/sys/fs/cgroup/cpuset{}/cpuset.cpus'.format(cg_name), 'r').readline().strip().split(',')))
    cg_memory = float(open('/sys/fs/cgroup/memory{}/memory.limit_in_bytes'.format(cg_name), 'r').readline().strip())
    CGROUP_INFO = {'name': cg_name, 'cpu': cg_cpus, 'memory': cg_memory}
    logger.info("cgroup info: {}".format(CGROUP_INFO))

    # subprocesses
    workers = []
    feeds = []

    client_count = 0
    app_to_users = defaultdict(list)

    # parse run_config
    for c in run_config['clients']:
        for _ in range(c.get('num', 1)):
            app_to_users[c['app']].append(
                {
                    'id': client_count,
                    'video_uri': c['video_uri'],
                    'weight': c.get('weight', 1.)
                }
            )
            client_count += 1

    # perform scheduling and allocation
    app_to_resource = {}    # default no allocation
    # inter-app allocation
    if run_config.get('inter_app_schedule', True):
        # use our smart scheduler
        allocator = Allocator(ScipySolver(fair=run_config.get('fair', False)))
        apps = app_to_users.keys()
        logger.info(apps)
        cpu_caps = map(lambda app: importlib.import_module(app).OMP_NUM_THREADS * len(app_to_users[app]), apps)
        success, _, res = allocator.solve(
            CGROUP_INFO['cpu'], CGROUP_INFO['memory']/GiB, map(AppUtil, apps), cpu_caps= )
        assert success
        alloted_cpu, alloted_mem = res[:len(res)//2], res[len(res)//2:] * GiB
        logger.info("solved cpu: {}".format(alloted_cpu))
        logger.info("solved mem: {}".format(alloted_mem))

        # rectify zero-cpu: if alloted CPU is too small, simply don't run it and re-allocate memory/cpu perseving ratio
        alloted_cpu[alloted_cpu < 0.2] = 0.
        alloted_cpu = CGROUP_INFO['cpu'] * alloted_cpu / np.sum(alloted_cpu)
        alloted_mem[alloted_cpu < 1e-3] = 0.
        alloted_mem = CGROUP_INFO['memory'] * alloted_mem / np.sum(alloted_mem)
        logger.info("rectified cpu: {}".format(alloted_cpu))
        logger.info("rectified mem: {}".format(alloted_mem))

        for app, cpu, mem in zip(apps, alloted_cpu, alloted_mem):
            omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS
            num_workers = int(math.ceil(cpu / float(omp_num_threads)))

            app_to_resource[app] = {
                'cpu': cpu, 'memory': mem, 'workers': num_workers
            }
        logger.info(app_to_resource)


    if component == 'client':
        client_count = 0

        for app, users in app_to_users.iteritems():
            if app_to_resource:
                app_tokens = app_to_resource[app]['workers']
            else:
                app_tokens = len(users)

            for u in users:
                token = 1 if app_tokens > 0 else 0
                app_tokens -= token
            
                if token > 0:
                    if not dry_run:
                        feeds.append(mp.Process(
                            target=start_feed, args=(app, u['video_uri'], 2, exp, u['id'],), name='client-'+str(u['id'])
                        ))
                else:
                    logger.warn("Drop user {} {}".format(app, u['id']))

    if component == 'server':
        for app, users in app_to_users.iteritems():
            docker_run_kwargs = {}
            num_workers = len(users)
            if app_to_resource:
                docker_run_kwargs = {
                    'cpu_period': int(100000), 
                    'cpu_quota': int(app_to_resource[app]['cpu'] * 100000), 
                    'mem_limit': int(app_to_resource[app]['memory'])
                    }
                num_workers = app_to_resource[app]['workers']
            
            logger.info("{} docker run kwargs: {}".format(app, docker_run_kwargs))

            if not docker_run_kwargs or docker_run_kwargs['cpu_quota'] > 1000:
                if not dry_run:
                    workers.append(mp.Process(
                        target=start_worker, args=(app, num_workers, docker_run_kwargs), name=app+'-server'))
            else:
                logger.warn("Dropping app {}".format(app))

    for p in workers + feeds:
        p.daemon = True
    try:
        if not dry_run:
            # start all endpoints
            map(lambda t: t.start(), workers + feeds)

            if component == 'client' and 'stop_after' in run_config:
                time.sleep(run_config['stop_after'])
                raise RuntimeError("run_config time's up")

            map(lambda t: t.join(), workers + feeds)

    except KeyboardInterrupt:
        pass
    finally:
        if not dry_run:
            logger.debug("Cleaning up processes")
            map(lambda t: t.terminate(), feeds + workers)
            if component == 'server':
                kill()


def kill():
    logger.info('Last effort to remove worker containers')
    ret = subprocess.check_output(
        "docker rm -f $(docker ps --filter 'name=rmexp-mc-*' -a -q)", shell=True)
    logger.info(ret)


if __name__ == "__main__":
    fire.Fire()
