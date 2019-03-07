#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

import ast
import collections
import multiprocessing
import os
import time

import cv2
import fire
import numpy as np
from logzero import logger

import const
import redis
from lego import lego
from utils import timeit

time_log = collections.defaultdict(list)


class RedisConnector(object):
    def __init__(self, host, port, db=0):
        super(RedisConnector, self).__init__()
        self.client = redis.Redis(host=host, port=port, db=db)

    def get(self):
        # blocking
        item = self.client.brpop([const.REDIS_STREAM_CHAN])
        return item


class JobQueue(object):
    def __init__(self, connector):
        super(JobQueue, self).__init__()
        self.connector = connector

    def get(self):
        return self.connector.get()


@timeit(time_log)
def process_request(lego_app, img):
    result = lego_app.handle_img(img)
    logger.debug(result)


def loop(job_queue, redis_logger):
    lego_app = lego.LegoHandler()
    redis_logger.client.flushdb()
    while True:
        _, item = job_queue.get()
        (encoded_im, ts) = ast.literal_eval(item)
        encoded_im_np = np.asarray(bytearray(encoded_im), dtype=np.uint8)
        img = cv2.imdecode(encoded_im_np, cv2.CV_LOAD_IMAGE_UNCHANGED)
        process_request(lego_app, img)
        redis_logger.client.lpush('process_time', (time.time() - ts) * 1000)
        logger.debug('[proc {}] takes {} ms for an item'.format(os.getpid(), (time.time() - ts) * 1000))


def start_process_loop(host, port):
    jq = JobQueue(RedisConnector(host, port))
    redis_logger = RedisConnector(host, port, db=1)
    loop(jq, redis_logger)


def start(num, host, port):
    procs = [multiprocessing.Process(target=start_process_loop, args=(
        host, port, )) for i in range(num)]
    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


def batch_process(video_uri):
    lego_app = lego.LegoHandler()
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    while has_frame:
        has_frame, img = cam.read()
        if img is not None:
            process_request(lego_app, img)
    logger.info(time_log)


if __name__ == "__main__":
    fire.Fire()
