#! /usr/bin/env python

from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import time

import cv2
import fire
from lego import lego_cv
from logzero import logger
from twisted.internet import reactor, task

from rmexp import dbutils, client, config, gabriel_pb2, networkutil
from rmexp.schema import models


def start_single_feed(video_uri, fps, broker_type, broker_uri):
    nc = networkutil.get_connector(broker_type, broker_uri)
    # TODO(junjuew): make video params to be cmd inputs
    vc = client.VideoClient(video_uri, nc, video_params={
                            'width': 640, 'height': 360})
    t = task.LoopingCall(vc.get_and_send_frame)
    # t = task.LoopingCall(vc.get_and_send_frame, filter_func=lego_cv.locate_board)
    t.start(1.0 / fps)
    reactor.run()


def start_single_feed_token(video_uri, app, broker_type, broker_uri, tokens_cap, exp='', client_id=0):
    if exp:
        sess = dbutils.get_session()

    nc = networkutil.get_connector(broker_type, broker_uri, client=True)
    vc = client.RTVideoClient(video_uri, nc)
    vc.start()
    tokens = tokens_cap
    while True:
        while tokens > 0:
            vc.get_and_send_frame(reply=True, app=app)
            tokens -= 1

        while True:
            r = nc.get(timeout=10)
            if r is None:
                break
            else:
                (service, msg) = r
                msg = msg[0]
                tokens += 1
                if service != app:
                    # this is due to some optimization happening such that my request
                    # is not processed
                    logger.debug(
                        'received message not from my server: {}'.format((service, msg)))
                    continue

                gabriel_msg = gabriel_pb2.Message()
                gabriel_msg.ParseFromString(msg)
                elapsed_ms = int((time.time() - gabriel_msg.timestamp) * 1000)
                logger.debug("Frame {}: {} ms : {}".format(
                    gabriel_msg.index, elapsed_ms, gabriel_msg.data))

                if exp:
                    index = '{}-{}'.format(client_id,
                                           gabriel_msg.index.split('-')[1])
                    dbutils.insert_or_update_one(
                        sess, models.ExpLatency,
                        {'name': exp, 'index': index, 'app': app},
                        {'val': elapsed_ms}
                    )
                    sess.commit()


def start(num, video_uri, broker_uri, app, fps=20, tokens=None, broker_type='kafka'):
    # if tokens is not None, use tokened client
    procs = list()
    for _ in range(num):
        if tokens is not None:
            p = multiprocessing.Process(target=start_single_feed_token,
                                        args=(video_uri, app, broker_type, broker_uri, tokens,))
        else:
            p = multiprocessing.Process(target=start_single_feed,
                                        args=(video_uri, fps, broker_type, broker_uri, ))

        p.daemon = True
        procs.append(p)

    try:
        map(lambda proc: proc.start(), procs)
        map(lambda proc: proc.join(), procs)
    finally:
        map(lambda p: p.terminate(), procs)


if __name__ == '__main__':
    fire.Fire()
