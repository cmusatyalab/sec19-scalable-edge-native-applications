#! /usr/bin/env python

from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import time

import cv2
import fire
from logzero import logger
from rmexp import config, gabriel_pb2, networkutil
from twisted.internet import reactor, task


def send_frame(frame, nc, *args, **kwargs):
    frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
    gabriel_msg = gabriel_pb2.Message()
    gabriel_msg.data = frame_bytes
    gabriel_msg.timestamp = time.time()
    nc.put(gabriel_msg.SerializeToString())


def get_frame(cam):
    has_frame, img = cam.read()
    if has_frame and img is not None:
        logger.debug('[proc {}] acquired frame'.format(os.getpid()))
        return img
    else:
        reactor.callFromThread(reactor.stop)
        raise ValueError("Failed to get another frame.")


def get_and_send_frame(cam, nc, *args, **kwargs):
    frame = get_frame(cam)
    send_frame(frame, nc, *args, **kwargs)


def get_video_capture(uri):
    cam = cv2.VideoCapture(uri)
    return cam


def start_single_feed(video_uri, fps, broker_type, broker_uri):
    nc = get_broker(broker_type, broker_uri)
    cam = get_video_capture(video_uri)
    t = task.LoopingCall(get_and_send_frame, cam, nc)
    t.start(1.0 / fps)
    reactor.run()


def get_broker(broker_type, broker_uri, *args, **kwargs):
    nc = None
    if broker_type == 'REDIS':
        import redis
        redis_client = redis.Redis(host=to_host, port=to_port)
        redis_client.flushdb()
    elif broker_type == 'zmq':
        nc = networkutil.ZmqConnector(broker_uri)
    elif broker_type == 'kafka':
        nc = networkutil.KafkaConnector(
            broker_uri, topic=config.STREAM_TOPIC, api_version=(2, 0, 1))
    return nc


def start(num, video_uri, broker_uri, fps=20, broker_type='kafka'):
    procs = [multiprocessing.Process(target=start_single_feed,
                                     args=(video_uri, fps, broker_type, broker_uri, )) for i in range(num)]
    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


if __name__ == '__main__':
    fire.Fire()
