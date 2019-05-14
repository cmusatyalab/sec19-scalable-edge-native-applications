#! /usr/bin/env python
from collections import defaultdict
import docker
import fire
import logging
import logzero
from logzero import logger
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
    cli = docker.from_env()

    container_name = 'rmexp-mc-{}-{}'.format(app, str(uuid.uuid4())[:8])

    bash_cmd = ". .envrc && OMP_NUM_THREADS=4 python rmexp/serve.py start --num {} \
                --broker-type {} --broker-uri {} --app {} " \
        .format(num, os.getenv('BROKER_TYPE'), os.getenv('WORKER_BROKER_URI'), app)
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
            exp=exp,
            client_id=client_id
        )
    except ValueError:
        logger.info("%s finished" % video_uri)


def intra_app_allocate(app, users, app_cpus, app_memory):
    # simple heuristics
    app_latency_4cpu = {
        'lego': 0.118,
        'face': 0.170,
        'pingpong': 0.032,
        'pool': 0.045
    }
    total_fps = (1./app_latency_4cpu[app]) * app_cpus / 4.0
    total_tokens = total_fps

    weights = np.array([u.get('weight', 1.) for u in users])
    weights = weights / np.sum(weights) # normalized

    allotted_tokens = (total_tokens * weights).astype(np.int) + 1

    for u, tokens in zip(users, allotted_tokens):
        u['tokens'] = tokens


def run(run_config, component, exp='', **kwargs):
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
    app_to_resource = dict()

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
    
    # inter-app allocation
    if run_config.get('inter_app_schedule', True):
        # use our smart scheduler
        allocator = Allocator(ScipySolver())
        apps = app_to_users.keys()
        weights = [sum(map(operator.itemgetter('weight'), app_to_users[a]))  for a in apps]
        success, _, res = allocator.solve(
            CGROUP_INFO['cpu'], CGROUP_INFO['memory']/GiB, map(AppUtil, apps), weights)
        assert success
        alloted_cpu, alloted_mem = res[:len(res)//2], res[len(res)//2:] * GiB
        app_to_resource = dict([
            (app, {'cpu': cpu, 'memory': mem}) 
            for app, cpu, mem in zip(apps, alloted_cpu, alloted_mem)
        ])
    else:
        # no allocation
        app_to_resource = {}

    # we don't do within-app differentiation for now
    # for app, users in app_to_users.iteritems():
    #     intra_app_allocate(app, users, app_to_resource[app]['cpus'], app_to_resource[app]['memory'])
    # logger.debug('Per user token: {}'.format(app_to_users))

    if component == 'client':
        client_count = 0

        for app, users in app_to_users.iteritems():
            for u in users:
                feeds.append(mp.Process(
                    target=start_feed, args=(app, u['video_uri'], 2, exp, u['id'],), name='client-'+str(u['id'])
                ))

    if component == 'server':
        for app, users in app_to_users.iteritems():
            docker_run_kwargs = {}
            if app_to_resource:
                docker_run_kwargs = {
                    'cpu_period': int(100000), 
                    'cpu_quota': int(app_to_resource[app]['cpu'] * 100000), 
                    'mem_limit': int(app_to_resource[app]['memory'])
                    }
            logger.info("{} docker run kwargs: {}".format(app, docker_run_kwargs))
            workers.append(mp.Process(
                target=start_worker, args=(app, min(40, 4*len(users)), docker_run_kwargs), name=app+'-server'))

    for p in workers + feeds:
        p.daemon = True
    try:
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
