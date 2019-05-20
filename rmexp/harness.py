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

def start_worker(app, num, docker_run_kwargs, busy_wait=None):
    omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS

    cli = docker.from_env()

    container_name = 'rmexp-harness-{}-{}-{}'.format(app, os.getppid(), str(uuid.uuid4())[:8])

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


def start_feed(app, video_uri, tokens_cap, exp='', client_id=0):
    # forced convert video_uri to frame dir
    if not os.path.isdir(video_uri):
        os.path.join(os.path.dirname(video_uri), 'video-images')

    logger.info('Starting client %d %s @ %s' % (client_id, app, video_uri))

    try:
        rmexp.feed.start_single_feed_token(
            video_uri,
            app,
            os.getenv('BROKER_TYPE'),
            os.getenv('CLIENT_BROKER_URI'),
            tokens_cap=tokens_cap,
            loop=True,
            random_start=False, # for sake of the same frames for different exps
            exp=exp,
            client_id=client_id
        )
    except ValueError:
        logger.info("%s finished" % video_uri)


def run(run_config, component, scheduler, exp='', dry_run=False, **kwargs):
    """[summary]

    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
        component -- 'client' or 'server'
        schduler {string} -- name of Python module that provides a schduler() function
        exp {string} -- if not empty, will write latency to DB
        dry_run {bool} -- if true, only print scheduling results and not run processes
        **kwargs -- override values in run_config
    """

    # parse role server/client
    component = component.lower()
    assert component in ['client', 'server'], 'Component needs to be either client or server'

    # parse run_config
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config, 'r'))
    run_config.update(kwargs)    

    # retrieve cgroup info
    global CGROUP_INFO
    cg_name = run_config.get('cgroup', CGROUP_INFO['name'])
    cpus_str = open('/sys/fs/cgroup/cpuset{}/cpuset.cpus'.format(cg_name), 'r').readline().strip()
    cg_cpus = sum(map(lambda t: int(t[-1]) - int(t[0]) + 1, map(lambda s: s.split('-'), cpus_str.split(','))))
    cg_memory = float(open('/sys/fs/cgroup/memory{}/memory.limit_in_bytes'.format(cg_name), 'r').readline().strip())
    CGROUP_INFO = {'name': cg_name, 'cpu': cg_cpus, 'memory': cg_memory}
    logger.info("cgroup info: {}".format(CGROUP_INFO))

    # subprocesses
    workers = []
    feeds = []

    # invoke scheduler
    sched_module = importlib.import_module(scheduler)
    start_worker_calls, start_feed_calls = sched_module.schedule(run_config, CGROUP_INFO['cpu'], CGROUP_INFO['memory'])

    # create subprocess
    if component == 'client':

        for call in start_feed_calls:
            call['kwargs']['exp'] = exp
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
        "docker rm -f $(docker ps --filter 'name=rmexp-harness-{}-*' -a -q)".format(os.getpid()), shell=True)
    logger.info(ret)


if __name__ == "__main__":
    fire.Fire()
