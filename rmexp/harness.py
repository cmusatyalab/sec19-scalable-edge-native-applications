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

# local
import feed

DOCKER_IMAGE = 'res'
CGROUP_INFO = {
    'name': '/rmexp'
}
GiB = 2.**30

# logger.setLevel(logging.DEBUG)


# configuration setup when dutycycle and imu is enabled
device_type_map = {
    'lego': 'dutycycleimu',
    'pingpong': 'dutycycleimu',
    'pool': 'dutycycleimu',
    'ikea': 'dutycycleimu',
    'face': 'baseline',
}

dutycycle_sampling_on_map = {
    'lego': True,
    'ikea': True,
    'pingpong': False,
    'pool': False,
    'face': False,
}

random_start_map = {
    'lego': True,
    'ikea': False,  # ikea fsm cannot handle random starts
    'pingpong': True,
    'pool': True,
    'face': True,
}


def start_worker(app, num, docker_run_kwargs, busy_wait=None):
    omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS

    cli = docker.from_env()

    container_name = 'rmexp-harness-{}-{}-{}'.format(
        os.getppid(), app, str(uuid.uuid4())[:8])

    bash_cmd = ". .envrc && OMP_NUM_THREADS={} python rmexp/serve.py start --num {} \
                --broker-type {} --broker-uri {} --app {} " \
        .format(omp_num_threads, num, os.getenv('BROKER_TYPE'), os.getenv('WORKER_BROKER_URI'), app)
    if busy_wait:
        bash_cmd += " --busy_wait {}".format(busy_wait)
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


def start_feed(app, video_uri, tokens_cap, stop_after,
               random_start=False, client_type='video', dutycycle_sampling_on=False,
               exp='', client_id=0):
    # forced convert video_uri to frame dir
    if not os.path.isdir(video_uri):
        video_uri = os.path.join(os.path.dirname(video_uri), 'video-images')

    logger.info('Starting client %d %s @ %s' % (client_id, app, video_uri))

    try:
        feed.start_single_feed_token(
            video_uri,
            app,
            os.getenv('BROKER_TYPE'),
            os.getenv('CLIENT_BROKER_URI'),
            tokens_cap=tokens_cap,
            loop=True,
            random_start=random_start,  # for sake of the same frames for different exps
            client_type=client_type,
            dutycycle_sampling_on=dutycycle_sampling_on,
            exp=exp,
            client_id=client_id,
            stop_after=stop_after
        )
    except ValueError:
        logger.info("%s finished" % video_uri)


def run(run_config, component, scheduler, exp='', dry_run=False, enable_dutycycleimu=False, **kwargs):
    """[summary]

    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
        component -- 'client' or 'server'
        schduler {string} -- name of Python module that provides a schduler() function
        exp {string} -- if not empty, will write latency to DB
        dry_run {bool} -- if true, only print scheduling results and not run processes
        enable_dutycycleimu {bool} -- if true, enable dutycycle and imu suppression on the client
        **kwargs -- override values in run_config
    """

    # parse role server/client
    component = component.lower()
    assert component in [
        'client', 'server'], 'Component needs to be either client or server'

    # parse run_config
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config, 'r'))
    run_config.update(kwargs)

    # quick hack for section 6
    # used to show dry_run results
    # simple_apps = ('lego', 'pingpong', 'face', 'pool', 'ikea', )
    # run_config['clients'] = run_config.get('clients', list())
    # for app in simple_apps:
    #     if app in run_config:
    #         run_config['clients'].append({
    #             'app': app, 'num': int(run_config[app]),
    #             'video_uri': 'dummy_video_uri'})

    # retrieve cgroup info
    global CGROUP_INFO
    cg_name = run_config.get('cgroup', CGROUP_INFO['name'])
    cpus_str = open(
        '/sys/fs/cgroup/cpuset{}/cpuset.cpus'.format(cg_name), 'r').readline().strip()
    cg_cpus = sum(map(lambda t: int(
        t[-1]) - int(t[0]) + 1, map(lambda s: s.split('-'), cpus_str.split(','))))
    cg_memory = float(open(
        '/sys/fs/cgroup/memory{}/memory.limit_in_bytes'.format(cg_name), 'r').readline().strip())
    CGROUP_INFO = {'name': cg_name, 'cpu': cg_cpus, 'memory': cg_memory}
    logger.info("cgroup info: {}".format(CGROUP_INFO))

    # subprocesses
    workers = []
    feeds = []

    # invoke scheduler
    sched_module = importlib.import_module(scheduler)
    start_worker_calls, start_feed_calls = sched_module.schedule(
        run_config, CGROUP_INFO['cpu'], CGROUP_INFO['memory'])

    # create subprocess
    if component == 'client':

        for call in start_feed_calls:
            if enable_dutycycleimu:
                # random start needs to be true to avoid synchronizations among clients
                app = call['kwargs']['app']
                if scheduler == 'baseline':
                    call['kwargs']['random_start'] = random_start_map[app]
                    call['kwargs']['client_type'] = 'baseline'
                    call['kwargs']['dutycycle_sampling_on'] = False
                else:
                    call['kwargs']['random_start'] = random_start_map[app]
                    call['kwargs']['client_type'] = device_type_map[app]
                    call['kwargs']['dutycycle_sampling_on'] = dutycycle_sampling_on_map[app]
            else:
                # this is for pure resource allocation experiments. making sure the frames processed are the same.
                call['kwargs']['random_start'] = False
                call['kwargs']['client_type'] = 'video'
                call['kwargs']['dutycycle_sampling_on'] = False
            call['kwargs']['exp'] = exp
            call['kwargs']['stop_after'] = run_config.get('stop_after', None)
            logger.debug("start feed: {}".format(call))

            if not dry_run:
                feeds.append(mp.Process(
                    target=start_feed, args=call['args'], kwargs=call['kwargs']
                ))

    if component == 'server':

        for call in start_worker_calls:
            logger.debug("start worker: {}".format(call))

            if not dry_run:
                workers.append(mp.Process(
                    target=start_worker, args=call['args'], kwargs=call['kwargs']
                ))

    if not dry_run:
        # Go
        try:
            for p in workers + feeds:
                p.daemon = True

            map(lambda t: t.start(), workers + feeds)

            if component == 'server':
                map(lambda t: t.join(), workers)  # workers run forever
            elif component == 'client':
                map(lambda t: t.join(), feeds)

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
        "docker rm -f $(docker ps --filter 'name=rmexp-harness-{}-*' -a -q)".format(os.getpid()), shell=True)
    logger.info(ret)


if __name__ == "__main__":
    fire.Fire()
