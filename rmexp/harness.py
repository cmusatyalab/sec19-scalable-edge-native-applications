#! /usr/bin/env python
from collections import defaultdict
import docker
import fire
from logzero import logger
import multiprocessing as mp
import os
import subprocess
import threading
import time
import uuid
import yaml

import rmexp.feed

DOCKER_IMAGE = 'res'
RMEXP_CGROUP = '/rmexp'


def start_worker(app, num, docker_run_kwargs):
    cli = docker.from_env()

    container_name = 'rmexp-mc-{}-{}'.format(app, str(uuid.uuid4())[:8])

    bash_cmd = ". .envrc && OMP_NUM_THREADS=4 python rmexp/serve.py start --num {} \
                --broker-type {} --broker-uri {} --app {} " \
        .format(num, os.getenv('BROKER_TYPE'), os.getenv('WORKER_BROKER_URI'), app)
    logger.debug(bash_cmd)

    try:
        logger.debug('Starting workers: {}x {} @ {}'.format(
            num, app, container_name))
        cli.containers.run(
            DOCKER_IMAGE,
            ['/bin/bash', '-i', '-c', bash_cmd],
            cgroup_parent=RMEXP_CGROUP,
            name=container_name,
            auto_remove=True,
            stderr=False,
            **docker_run_kwargs
        )
    finally:
        pass


def start_feed(app, video_uri, exp='', client_id=0):
    logger.debug('Starting client %d %s @ %s' % (client_id, app, video_uri))

    try:
        rmexp.feed.start_single_feed_token(
            video_uri,
            app,
            os.getenv('BROKER_TYPE'),
            os.getenv('CLIENT_BROKER_URI'),
            tokens_cap=5,
            exp=exp,
            client_id=client_id
        )
    except ValueError:
        logger.debug("%s finished" % video_uri)


def run(run_config, component, exp=''):
    """[summary]

    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
        component: 'client' or 'server'
    """
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config, 'r'))
    component = component.lower()
    assert component in [
        'client', 'server'], 'Component needs to be either client or server'

    workers = []
    feeds = []

    # parse run_config file
    app_user_count = defaultdict(int)
    for client in run_config['clients']:
        for i in range(client.get('num', 1)):
            app = client['app']
            app_user_count[app] += 1

    if component == 'client':
        client_count = 0
        for client in run_config['clients']:
            for i in range(client.get('num', 1)):
                app, video_uri = client['app'], client['video_uri']
                feeds.append(mp.Process(
                    target=start_feed, args=(
                        app, video_uri, exp, client_count),
                    name=client['video_uri']+'-' + str(i)))
                client_count += 1

    if component == 'server':
        for app, count in app_user_count.iteritems():
            # do some smart here
            # docker_run_kwargs = {'cpu_period': 100000, 'cpu_quota': 150000}
            docker_run_kwargs = {}
            workers.append(mp.Process(
                target=start_worker, args=(app, min(20, 2*count), docker_run_kwargs), name=app+'-server'))

    for p in workers + feeds:
        p.daemon = True
    try:
        # start all endpoints
        map(lambda t: t.start(), workers + feeds)
        map(lambda t: t.join(), workers + feeds)
    except KeyboardInterrupt:
        pass
    finally:
        logger.debug("Cleaning up processes")
        map(lambda t: t.terminate(), feeds + workers)
        if component == 'server':
            kill()


def kill():
    logger.debug('Last effort to remove worker containers')
    ret = subprocess.check_output(
        "docker rm -f $(docker ps --filter 'name=rmexp-mc-*' -a -q)", shell=True)
    logger.debug(ret)


if __name__ == "__main__":
    fire.Fire()
