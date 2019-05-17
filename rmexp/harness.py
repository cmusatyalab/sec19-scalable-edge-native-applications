#! /usr/bin/env python
from collections import defaultdict
import docker
import fire
import importlib
import itertools
import json
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


def best_workers(app, cpu, memory=None):
    # solely based on cpu now
    omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS
    return int(math.ceil(cpu / float(omp_num_threads)))


def run(run_config, component, strategy="ours", exp='', dry_run=False, **kwargs):
    """[summary]

    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
        component -- 'client' or 'server'
        strategy {string} -- 'ours', 'baseline'
        exp {string} -- if not empty, will write latency to DB
        dry_run {bool} -- if true, only print scheduling results and not run processes
        **kwargs -- override values in run_config
    """

    # parse role server/client
    component = component.lower()
    assert component in ['client', 'server'], 'Component needs to be either client or server'

    # parse run_config
    client_count = 0
    app_to_users = defaultdict(list)
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config, 'r'))
    run_config.update(kwargs)    
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

    # perform scheduling and allocation
    app_to_resource = {}    # app -> {'cpu'=, 'memory'=, 'workers'=, admission'=,}
    if strategy == 'ours':
        logger.info("Using our scheduler")
        allocator = Allocator(ScipySolver(fair=run_config.get('fair', False)))
        flatten_apps = list(itertools.chain.from_iterable([ [app]*len(users) for app, users in app_to_users.iteritems()]))
        logger.debug(flatten_apps)
        success, _, res = allocator.solve(CGROUP_INFO['cpu'], CGROUP_INFO['memory']/GiB, map(AppUtil, flatten_apps))
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

        # write back to users' info
        for u, c, m in zip(
            itertools.chain.from_iterable([ users for _, users in app_to_users.iteritems()]),
            alloted_cpu, alloted_mem):
            u['cpu'], u['memory'] = c, m
            
        # group resources by app
        for app, users in app_to_users.iteritems():
            app_to_resource[app] = {
                'cpu': sum(map(operator.itemgetter('cpu'), users)),
                'memory': sum(map(operator.itemgetter('memory'), users))
            }
            app_to_resource[app].update({
                'workers': best_workers(app, app_to_resource[app]['cpu']),
                'admission': best_workers(app, app_to_resource[app]['cpu'])
            })
    elif strategy == "baseline":
        logger.info("Using baseline scheduler")
        for app, users in app_to_users.iteritems():
            app_to_resource[app] = {
                'cpu': CGROUP_INFO['cpu'],
                'memory': CGROUP_INFO['memory'],
                'workers': best_workers(app, CGROUP_INFO['cpu']),
                'admission': best_workers(app, CGROUP_INFO['cpu'])  # each app does admission based on global resource
            }
    else:
        raise ValueError("Unknown strategy: {}".format(strategy))

    # logger.info(app_to_users)
    logger.info(json.dumps(app_to_resource, indent=2))

    if component == 'client':

        for app, users in app_to_users.iteritems():
            admission = app_to_resource[app]['admission']

            for u in users:
                if admission > 0:
                    logger.info("Accept user {} {}".format(app, u['id']))
                    if not dry_run:
                        feeds.append(mp.Process(
                            target=start_feed, args=(app, u['video_uri'], 2, exp, u['id'],), name='client-'+str(u['id'])
                        ))
                    admission -= 1
                else:
                    logger.warn("Drop user {} {}".format(app, u['id']))

    if component == 'server':
        for app, res in app_to_resource.iteritems():
            if res['cpu'] < 0.1:
                logger.warn("Drop App {}".format(app))
                continue

            docker_run_kwargs = {
                'cpu_period': int(100000), 
                'cpu_quota': int(res['cpu'] * 100000), 
                'mem_limit': int(res['memory'])
                }
            num_workers = res['workers']

            if not dry_run:
                workers.append(mp.Process(
                    target=start_worker, args=(app, num_workers, docker_run_kwargs), name=app+'-server'))

    if not dry_run:
        try:
            for p in workers + feeds:
                p.daemon = True
            # start all endpoints
            map(lambda t: t.start(), workers + feeds)

            if component == 'client' and 'stop_after' in run_config:
                time.sleep(run_config['stop_after'])
                raise RuntimeError("run_config time's up")

            map(lambda t: t.join(), workers + feeds)

        except KeyboardInterrupt:
            pass
        finally:
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
