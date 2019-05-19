#! /usr/bin/env python

from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import time
import datetime

import cv2
import fire
from lego import lego_cv
from logzero import logger

from rmexp import dbutils, client, config, gabriel_pb2, networkutil, utils
from rmexp.schema import models
from rmexp.client import emulator

import logzero


# def start_single_feed(video_uri, fps, broker_type, broker_uri):
#     from twisted.internet import reactor, task
#     nc = networkutil.get_connector(broker_type, broker_uri)
#     # TODO(junjuew): make video params to be cmd inputs
#     vc = client.VideoClient(video_uri, nc, video_params={
#                             'width': 640, 'height': 360})
#     t = task.LoopingCall(vc.get_and_send_frame)
#     # t = task.LoopingCall(vc.get_and_send_frame, filter_func=lego_cv.locate_board)
#     t.start(1.0 / fps)
#     reactor.run()


def store_exp_latency(dbobj, gabriel_msg):
    reply_ms = int(1000 * (time.time() - gabriel_msg.timestamp))
    arrival_ms = int(
        1000 * (gabriel_msg.arrival_ts - gabriel_msg.timestamp))
    finished_ms = int(
        1000 * (gabriel_msg.finished_ts - gabriel_msg.timestamp))
    index = gabriel_msg.index.split('-')[1]

    sess, exp, app, client_id = dbobj['sess'], dbobj['exp'], dbobj['app'], dbobj['client_id']
    if sess is not None:
        sess = dbobj['sess']
        dbutils.insert_or_update_one(
            sess, models.ExpLatency,
            {'name': exp, 'index': index, 'app': app,
                'client': str(client_id)},
            {'arrival': arrival_ms,
                'finished': finished_ms, 'reply': reply_ms}
        )
        sess.commit()
    else:
        print(
            ','.join(map(str,
                         [exp, index, app, client_id, arrival_ms, finished_ms, reply_ms])))
    logger.debug("{}: E2E {} ms : {}".format(
        gabriel_msg.index, reply_ms, gabriel_msg.data))


def run_loop(vc, nc, tokens_cap, dbobj=None):
    tokens = tokens_cap
    while True:
        while tokens > 0:
            vc.get_and_send_frame(reply=True)
            tokens -= 1

        while True:
            r = nc.get(timeout=5)
            if r is None:
                break
            else:
                (service, msg) = r
                msg = msg[0]
                tokens += 1
                gabriel_msg = gabriel_pb2.Message()
                gabriel_msg.ParseFromString(msg)
                vc.process_reply(gabriel_msg.data)
                if dbobj is not None:
                    store_exp_latency(dbobj, gabriel_msg)


def start_single_feed_token(video_uri, app, broker_type, broker_uri, tokens_cap,
                            loop=True, random_start=True, exp='', client_id=0, client_type='video', print_only=False):
    nc = networkutil.get_connector(broker_type, broker_uri, client=True)
    vc = None
    if client_type == 'video':
        vc = client.RTVideoClient(
            app, video_uri, nc, loop=False, random_start=False)
    elif client_type == 'device':
        trace = utils.video_uri_to_trace(video_uri)
        cam = emulator.VideoAdaptiveSensor(
            trace, network_connector=nc, loop=loop, random_start=random_start)
        imu = emulator.IMUSensor(trace)
        device = emulator.IMUSuppresedCameraTimedMobileDevice(
            sensors=[cam, imu]
        )
        vc = emulator.DeviceToClientAdapter(device)
    else:
        raise ValueError('Not Supoprted client_type {}'.format(client_type))
    dbobj = None
    if exp:
        if print_only:
            sess = None
        else:
            sess = dbutils.get_session()
        dbobj = {
            'sess': sess,
            'exp': exp,
            'client_id': client_id,
            'app': app
        }
    run_loop(vc, nc, tokens_cap, dbobj=dbobj)


def start(num, video_uri, app, broker_type, broker_uri, tokens_cap,
          loop=True, random_start=True, exp='', client_id=0, client_type='device'):
    # if tokens is not None, use tokened client
    procs = list()
    for _ in range(num):
        p = multiprocessing.Process(target=start_single_feed_token,
                                    args=(video_uri, app, broker_type, broker_uri, tokens_cap,
                                          loop, random_start, exp, client_id, client_type))

        p.daemon = True
        procs.append(p)

    try:
        map(lambda proc: proc.start(), procs)
        map(lambda proc: proc.join(), procs)
    finally:
        map(lambda p: p.terminate(), procs)


if __name__ == '__main__':
    fire.Fire()
