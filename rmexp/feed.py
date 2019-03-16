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
from rmexp import networkutil


def send_frame_redis(frame, redis_client):
    frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
    redis_client.lpush(config.REDIS_STREAM_CHAN, (frame_bytes, time.time()))


def send_frame(frame, *args, **kwargs):
    # send_frame_redis(frame, *args, **kwargs)
    frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
    nc = kwargs['nc']
    nc.send(frame_bytes, time.time())
    # redis_client.lpush(config.REDIS_STREAM_CHAN, (frame_bytes, time.time()))


def get_frame(cam):
    has_frame, img = cam.read()
    if has_frame and img is not None:
        logger.debug('[proc {}] acquired frame'.format(os.getpid()))
        return img
    else:
        reactor.callFromThread(reactor.stop)
        raise ValueError("Failed to get another frame.")


def get_and_send_frame(cam, *args, **kwargs):
    frame = get_frame(cam)
    send_frame(frame, *args, **kwargs)


def get_video_capture(uri):
    cam = cv2.VideoCapture(uri)
    return cam


def start_single_feed(nc, fps):
    cam = get_video_capture(uri)
    # redis_client = redis.Redis(host=to_host, port=to_port)
    t = task.LoopingCall(get_and_send_frame, cam, nc)
    t.start(1.0 / fps)
    reactor.run()


def start(num, uri, to_host, to_port, fps=20):
    # redis_client = redis.Redis(host=to_host, port=to_port)
    # redis_client.flushdb()
    nc = networkutil.ZmqConnector("tcp://{}:{}".format(to_host, to_port))
    procs = [multiprocessing.Process(target=start_single_feed, args=(
        nc, fps, )) for i in range(num)]
    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


if __name__ == '__main__':
    fire.Fire()
