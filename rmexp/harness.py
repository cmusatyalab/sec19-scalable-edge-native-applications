#! /usr/bin/env python
import docker
import fire
from logzero import logger
import multiprocessing as mp
import os
import subprocess
import threading
import uuid
import yaml

import rmexp.feed

DOCKER_IMAGE = 'res'


def start_worker(app):
    cli = docker.from_env()
    env = {
        'EXP': '',
    }
    container_name = 'rmexp-%s-' % app + str(uuid.uuid4())

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
            environment=env,
            auto_remove=True,
            stderr=False,
            stdout=False,
            tty=True
        )
    finally:
        try:
            logger.debug('Last effort to remove %s' % container_name)
            cli.containers.get(container_name).remove(force=True)
        except:
            logger.debug('Failed: Last effort to remove %s' % container_name)
            pass

def start_feed(app, video_uri):
    logger.debug('Starting feed %s @ %s' % (app, video_uri))

    try:
        rmexp.feed.start_single_feed_token(
            video_uri,
            app,
            os.getenv('BROKER_TYPE'),
            os.getenv('CLIENT_BROKER_URI'),
            tokens_cap=5
        )
    except ValueError:
        logger.debug("%s finished" % video_uri)


def run(run_config):
    """[summary]
    
    Arguments:
        run_config {dict or string} -- if string, load json/yaml from file
    """
    if not isinstance(run_config, dict):
        run_config = yaml.load(open(run_config))

    workers = []
    feeds = []

    for client in run_config['clients']:
        for i in range(client.get('num', 1)):
            workers.append(mp.Process(
                target=start_worker, args=(client['app'],), name=client['app']+'-wrk-'+str(i)))
            feeds.append(mp.Process(
                target=start_feed, args=(client['app'], client['video_uri'],),
                name=client['video_uri']+'-'+ str(i) ))

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


if __name__ == "__main__":
    fire.Fire()
