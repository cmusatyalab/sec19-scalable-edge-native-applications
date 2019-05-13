#! /usr/bin/env python
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


def start_worker(app, **kwargs):
    cli = docker.from_env()

    container_name = 'rmexp-mc-%s-%s' % (app, str(uuid.uuid4())[:8])

    bash_cmd = ". .envrc && OMP_NUM_THREADS=4 python rmexp/serve.py start --num 1 \
                --broker-type {} --broker-uri {} --app {} " \
        .format(os.getenv('BROKER_TYPE'), os.getenv('WORKER_BROKER_URI'), app)
    logger.debug(bash_cmd)

    try:
        logger.debug('Starting worker: %s @ %s' % (app, container_name))
        cli.containers.run(
            DOCKER_IMAGE,
            ['/bin/bash', '-i', '-c', bash_cmd],
            name=container_name,
            auto_remove=True,
            stderr=False,
            stdout=False,
            tty=True
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


def run(run_config, exp=''):
    """[summary]
    
    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
    """
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config))

    workers = []
    feeds = []
    client_count = 0

    for client in run_config['clients']:
        for i in range(client.get('num', 1)):
            workers.append(mp.Process(
                target=start_worker, args=(client['app'],), name=client['app']+'-wrk-'+str(i)))
            feeds.append(mp.Process(
                target=start_feed, args=(client['app'], client['video_uri'], exp, client_count),
                name=client['video_uri']+'-'+ str(i) ))
            client_count += 1

    for p in workers + feeds:
        p.daemon = True
    
    try:
        # start all endpoints
        map(lambda t: t.start(), workers + feeds)
        # join clients
        map(lambda t: t.join(), feeds)
    except KeyboardInterrupt:
        pass
    finally:
        logger.debug("Cleaning up processes")
        map(lambda t: t.terminate(), feeds + workers)

    logger.debug('Last effort to remove worker containers')
    ret = subprocess.check_output("docker rm -f $(docker ps --filter 'name=rmexp-mc-*' -a -q)", shell=True)
    logger.debug(ret)



if __name__ == "__main__":
    fire.Fire()
