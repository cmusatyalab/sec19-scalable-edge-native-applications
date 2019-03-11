#! /usr/bin/env python

from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import time

import cv2
import fire
from logzero import logger
from twisted.internet import reactor, task

import redis
from rmexp import config


# TODO(junjuew): finish this?
def start(num, uri, to_host, to_port, fps=20):
    redis_client = redis.Redis(host=to_host, port=to_port)
    pubsub = redis_client.pubsub()
    pubsub.subscribe(config.REDIS_RESPONSE_CHAN)
    running = True
    while running:
        message = pubsub.get_message()
        data = message['data']


if __name__ == '__main__':
    fire.Fire()
