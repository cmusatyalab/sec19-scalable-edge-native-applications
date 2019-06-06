#! /usr/bin/env python

from __future__ import absolute_import, division, print_function

import datetime
import logging
import multiprocessing
import os
import random
import time

import cv2
import fire
import logzero
from lego import lego_cv
from logzero import logger
from rmexp import client, config, dbutils, gabriel_pb2, networkutil, utils
from rmexp.client import emulator
from rmexp.client.video import RTImageSequenceClient, RTVideoClient
from rmexp.schema import models
from rmexp.utilityfunc import app_default_utility_func

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


def store_exp_latency(dbobj, gabriel_msg, util_fn, output):
    exp, app, client_id, trace_id = dbobj['exp'], dbobj['app'], dbobj['client_id'], dbobj['trace_id']

    reply_ms = int(1000 * (time.time() - gabriel_msg.timestamp))
    arrival_ms = int(
        1000 * (gabriel_msg.arrival_ts - gabriel_msg.timestamp))
    finished_ms = int(
        1000 * (gabriel_msg.finished_ts - gabriel_msg.timestamp))
    utility = float(util_fn(reply_ms))

    index = gabriel_msg.index.split('-')[1]

    if dbobj['sess'] is not None:
        record = models.ExpLatency(
            name=exp, index=index, app=app, client=str(client_id),
            arrival=arrival_ms, finished=finished_ms,
            reply=reply_ms, utility=utility, val=trace_id, result=gabriel_msg.data
        )
        output.append(record)

    else:
        print(
            ',,'.join(map(str,
                          [exp, index, app, client_id, arrival_ms, finished_ms, reply_ms, utility,
                           gabriel_msg.data])))

    logger.debug("{}: E2E {} ms : {} utility {}".format(
        gabriel_msg.index, reply_ms, gabriel_msg.data, utility))


def run_loop(vc, nc, tokens_cap, dbobj=None, util_fn=None, stop_after=None):
    start = time.time()
    tokens = tokens_cap
    output = list()

    while True:
        if stop_after and time.time() - start > stop_after:
            logger.info("Time's up ({}). Exiting loop".format(stop_after))
            break

        while tokens > 0:
            vc.get_and_send_frame(reply=True)
            tokens -= 1

        while True:
            r = nc.get(timeout=5)
            if r is None:
                break
            else:
                tic = time.time()
                (service, msg) = r
                msg = msg[0]
                tokens += 1
                gabriel_msg = gabriel_pb2.Message()
                gabriel_msg.ParseFromString(msg)
                vc.process_reply(gabriel_msg)
                if dbobj is not None:
                    store_exp_latency(dbobj, gabriel_msg, util_fn, output)

                logger.debug("Took {} secs to from recv to finish processing reply. DB: {}".format(
                    time.time() - tic, bool(dbobj)))

    if dbobj and 'sess' in dbobj:
        sess = dbobj['sess']
        logger.info("[pid {}] Committing changes to DB.".format(os.getpid()))
        sess.add_all(output)
        sess.commit()
        logger.info("[pid {}] Commited".format(os.getpid()))


def start_single_feed_token(video_uri,
                            app,
                            broker_type,
                            broker_uri,
                            tokens_cap,
                            dutycycle_sampling_on=False,
                            loop=True,
                            random_start=True,
                            exp='',
                            client_id=0,
                            client_type='video',
                            print_only=False,
                            stop_after=None):
    if print_only:
        logzero.loglevel(logging.CRITICAL)
    nc = networkutil.get_connector(broker_type, broker_uri, client=True)
    vc = None
    time.sleep(random.random() * 10.0)
    if client_type == 'video':
        if os.path.isdir(video_uri):
            vc = RTImageSequenceClient(
                app, video_uri, nc, loop=loop, random_start=random_start)
        else:
            assert os.path.isfile(video_uri)
            vc = client.RTVideoClient(
                app, video_uri, nc, loop=loop, random_start=random_start)
    elif client_type == 'baseline':
        trace = utils.video_uri_to_trace(video_uri)
        cam = emulator.VideoAdaptiveSensor(
            trace,
            dutycycle_sampling_on=False,
            video_uri=video_uri,
            network_connector=nc,
            loop=loop,
            random_start=random_start)
        device = emulator.CameraTimedMobileDevice(
            sensors=[cam]
        )
        vc = emulator.DeviceToClientAdapter(device)
    elif client_type == 'dutycycle':
        trace = utils.video_uri_to_trace(video_uri)
        cam = emulator.VideoAdaptiveSensor(
            trace,
            dutycycle_sampling_on=True,
            video_uri=video_uri,
            network_connector=nc,
            loop=loop,
            random_start=random_start)
        device = emulator.CameraTimedMobileDevice(
            sensors=[cam]
        )
        vc = emulator.DeviceToClientAdapter(device)
    elif client_type == 'dutycycleimu':
        trace = utils.video_uri_to_trace(video_uri)
        cam = emulator.VideoAdaptiveSensor(
            trace,
            dutycycle_sampling_on=dutycycle_sampling_on,
            video_uri=video_uri,
            network_connector=nc,
            loop=loop,
            random_start=random_start)
        imu = emulator.IMUSensor(trace)
        device = emulator.IMUSuppresedCameraTimedMobileDevice(
            sensors=[cam, imu]
        )
        vc = emulator.DeviceToClientAdapter(device)
    else:
        raise ValueError('Not Supoprted client_type {}'.format(client_type))
    dbobj = None
    db_dry_run = bool(not exp or print_only)
    with dbutils.session_scope(dry_run=db_dry_run) as sess:
        trace_id = str(int(video_uri.rstrip('/').split('/')[-2]))
        dbobj = {
            'sess': sess,
            'exp': exp,
            'client_id': client_id,
            'trace_id': trace_id,
            'app': app
        }
        util_fn = app_default_utility_func[app]
        run_loop(vc, nc, tokens_cap, dbobj=dbobj,
                 util_fn=util_fn, stop_after=stop_after)


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
