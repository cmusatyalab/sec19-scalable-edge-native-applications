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
    t = task.LoopingCall(vc.get_and_send_frame,
                         filter_func=lego_cv.locate_board)
    t.start(1.0 / fps)
    reactor.run()


def start(num, video_uri, broker_uri, fps=20, broker_type='kafka'):
    procs = [multiprocessing.Process(target=start_single_feed,
                                     args=(video_uri, fps, broker_type, broker_uri, )) for i in range(num)]
    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


if __name__ == '__main__':
    fire.Fire()
