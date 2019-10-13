from __future__ import absolute_import, division, print_function

import json
import logging
import os
import time
import importlib
import multiprocessing

import cv2
import fire
import logzero
from logzero import logger
import numpy as np

from rmexp import config, cvutils, dbutils, gabriel_pb2, client
from rmexp.schema import models

logzero.formatter(logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s', datefmt='%H:%M:%S'))
logzero.loglevel(logging.DEBUG)


def work_loop(job_queue, app, busy_wait=None):
    """[summary]

    Arguments:
        job_queue {[type]} -- [description]
        app {[type]} -- [description]

    Keyword Arguments:
        busy_wait {float} -- if not None, busy spin seconds instead of running actual app (default: {None})
    """
    handler = importlib.import_module(app).Handler()

    while True:
        get_ts = time.time()
        msg = job_queue.get()[0]
        get_wait = time.time() - get_ts
        if get_wait > 2e-3:
            logger.warn("[pid {}] took {} ms to get a new request. Maybe waiting".format(
                os.getpid(), int(1000 * get_wait)))

        arrival_ts = time.time()

        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.ParseFromString(msg)
        encoded_im, ts = gabriel_msg.data, gabriel_msg.timestamp

        logger.debug("[pid {}] about to process frame {}".format(
            os.getpid(), gabriel_msg.index))

        cts = time.clock()
        if not busy_wait:
            # do real work
            encoded_im_np = np.frombuffer(encoded_im, dtype=np.uint8)
            img = cv2.imdecode(encoded_im_np, cv2.CV_LOAD_IMAGE_UNCHANGED)
            result = handler.process(img)
        else:
            # busy wait fixed time
            tic = time.time()
            while True:
                if time.time() - tic > busy_wait:
                    break
            result = 'busy wait {}'.format(busy_wait)

        finished_ts = time.time()
        time_lapse = (finished_ts - ts) * 1000
        cpu_proc_ms = round((time.clock() - cts) * 1000)

        if gabriel_msg.reply:
            reply = gabriel_pb2.Message()
            reply.data = str(result)
            reply.timestamp = gabriel_msg.timestamp
            reply.index = gabriel_msg.index
            reply.finished_ts = finished_ts
            reply.arrival_ts = arrival_ts
            reply.cpu_proc_ms = cpu_proc_ms
            job_queue.put([reply.SerializeToString(), ])

        logger.debug('[pid {}] takes {} ms (cpu: {} ms) for frame {}: {}.'.format(
            os.getpid(), (time.time() - ts) * 1000, cpu_proc_ms, gabriel_msg.index, result))


class Sampler(object):
    """A Class to sample video stream. Designed to work with cam.read().
    Sample once every sample_period calls
    """

    def __init__(self, sample_period, sample_func=None):
        super(Sampler, self).__init__()
        self._sp = sample_period
        assert(type(sample_period) is int and sample_period > 0)
        self._sf = sample_func
        self._cnt = 0

    def sample(self):
        while True:
            self._cnt = (self._cnt + 1) % self._sp
            if self._cnt == 0:
                return self._sf()
            self._sf()


def process_and_time(img, app_handler):
    ts = time.time()
    result = app_handler.process(img)
    time_lapse = int(round((time.time() - ts) * 1000))
    return result, time_lapse


def store(
        data,
        session,
        store_result,
        store_latency,
        store_profile,
        **kwargs):
    name, trace, idx, result, time_lapse = data
    if store_result:
        rec, _ = dbutils.get_or_create(
            session,
            models.SS,
            name=name,
            index=idx,
            trace=trace)
        rec.val = str(result)
    if store_latency:
        rec, _ = dbutils.get_or_create(
            session,
            models.LegoLatency,
            name=name,
            index=idx)
        rec.val = int(time_lapse)
    if store_profile:
        rec = kwargs
        rec.update(
            {'trace': trace,
             'index': idx,
             'name': name,
             'latency': time_lapse
             }
        )
        dbutils.insert(
            session,
            models.ResourceLatency,
            rec
        )


def batch_process(video_uri,
                  app,
                  experiment_name,
                  trace=None,
                  store_result=False,
                  store_latency=False,
                  store_profile=False,
                  **kwargs):
    """Batch process a video. Able to store both the result and the frame processing latency.

    Arguments:
        video_uri {string} -- Video URI
        app {string} -- Applicaiton name
        experiment_name {string} -- Experiment name

    Keyword Arguments:
        trace {string} -- Trace id
        store_result {bool} -- Whether to store result into database
        store_result {bool} -- [description] (default: {False})
        store_latency {bool} -- [description] (default: {False})
        cpu {string} -- No of CPUs used. Used to populate profile database
        memory {string} -- No of memory used. Used to populate profile database
        num_worker {int} -- No of simultaneous workers. Used to populate profile database
    """
    if trace is None:
        trace = os.path.basename(os.path.dirname(video_uri))

    app = importlib.import_module(app)
    app_handler = app.Handler()
    vc = client.VideoClient(
        app.__name__, video_uri, None, loop=False, random_start=False)

    idx = 1
    with dbutils.session_scope() as session:
        for img in vc.get_frame_generator():
            cpu_time_ts = time.clock()
            result, time_lapse = process_and_time(img, app_handler)
            logger.debug("[pid: {}] processing frame {} from {}. {} ms".format(os.getpid(),
                                                                               idx, video_uri, int(time_lapse)))
            logger.debug(result)
            store(
                (experiment_name, trace, idx, result, time_lapse),
                session,
                store_result,
                store_latency,
                store_profile,
                **kwargs
            )
            idx += 1


def phash(video_uri):
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    with dbutils.session_scope(dry_run=False) as sess:
        trace_name = os.path.basename(os.path.dirname(video_uri))
        idx = 1
        while has_frame:
            has_frame, img = cam.read()
            if img is not None:
                cur_hash = cvutils.phash(img)
                sess.add(models.SS(
                    name='{}-f{}-phash'.format(trace_name, idx),
                    val=str(cur_hash),
                    trace=trace_name))
            idx += 1


def phash_diff_adjacent_frame(video_uri, output_dir):
    cam = cv2.VideoCapture(video_uri)
    os.makedirs(output_dir)
    has_frame = True
    prev_hash = None
    idx = 1
    logger.debug('calculating phash diff for adjacent frames')
    while has_frame:
        has_frame, img = cam.read()
        if img is not None:
            cur_hash = cvutils.phash(img)
            if prev_hash is not None:
                diff = cur_hash - prev_hash
                cv2.putText(img, 'diff={}'.format(
                    diff), (int(img.shape[1] / 3), img.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), thickness=5)
                cv2.imwrite(os.path.join(
                    output_dir, '{:010d}.jpg'.format(idx)), img)
                logger.debug(diff)
            prev_hash = cur_hash
            idx += 1


if __name__ == "__main__":
    fire.Fire()
