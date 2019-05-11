#! /usr/bin/env python

from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import time

import cv2
import fire
from lego import lego_cv
from logzero import logger
from rmexp import client, config, gabriel_pb2, networkutil
from twisted.internet import reactor, task


def start_single_feed(video_uri, fps, broker_type, broker_uri):
    nc = networkutil.get_connector(broker_type, broker_uri)
    # TODO(junjuew): make video params to be cmd inputs
    vc = client.VideoClient(video_uri, nc, video_params={
                            'width': 640, 'height': 360})
    t = task.LoopingCall(vc.get_and_send_frame)
    # t = task.LoopingCall(vc.get_and_send_frame, filter_func=lego_cv.locate_board)
    t.start(1.0 / fps)
    reactor.run()


def start_single_feed_token(video_uri, broker_type, broker_uri, tokens_cap):
    nc = networkutil.get_connector(broker_type, broker_uri)
    vc = client.RTVideoClient(video_uri, nc, video_params={
                                'width': 640, 'height': 360})
    vc.start()
    tokens = tokens_cap
    while True:
        while tokens > 0:
            vc.get_and_send_frame(reply=True)
            tokens -= 1
        
        while True:
            r = nc.get(timeout=10)
            if r is None:
                break
            else:
                tokens += 1
                tag, msg = r
                gabriel_msg = gabriel_pb2.Message()
                gabriel_msg.ParseFromString(msg)
                logger.debug("Frame {} get reply: {}".format(gabriel_msg.index, gabriel_msg.data))


def start(num, video_uri, broker_uri, fps=20, tokens=None, broker_type='kafka'):
    # use tokens is not None, use tokened client
    procs = list()
    for _ in range(num):
        if tokens is not None:
            p = multiprocessing.Process(target=start_single_feed_token,
                                        args=(video_uri, broker_type, broker_uri, tokens,))
        else:
            p = multiprocessing.Process(target=start_single_feed,
                                        args=(video_uri, fps, broker_type, broker_uri, ))        
        procs.append(p)

    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


if __name__ == '__main__':
    fire.Fire()
