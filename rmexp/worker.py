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
import numpy as np
from logzero import logger
from rmexp import config, cvutils, dbutils, gabriel_pb2, client
from rmexp.schema import models

logzero.loglevel(logging.DEBUG)


def work_loop(job_queue, app):
    handler = importlib.import_module(app).Handler()

    while True:
        msg = job_queue.get()[0]
        arrival_ts = time.time()
        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.ParseFromString(msg)
        encoded_im, ts = gabriel_msg.data, gabriel_msg.timestamp
        encoded_im_np = np.asarray(bytearray(encoded_im), dtype=np.uint8)
        img = cv2.imdecode(encoded_im_np, cv2.CV_LOAD_IMAGE_UNCHANGED)
        result = handler.process(img)
        finished_ts = time.time()
        time_lapse = (finished_ts - ts) * 1000

        if gabriel_msg.reply:
            reply = gabriel_pb2.Message()
            reply.data = str(result)
            reply.timestamp = gabriel_msg.timestamp
            reply.index = gabriel_msg.index
            reply.finished_ts = finished_ts
            reply.arrival_ts = arrival_ts
            job_queue.put([reply.SerializeToString(), ])

        logger.debug(result)
        logger.debug('[proc {}] takes {} ms for frame {}'.format(
            os.getpid(), (time.time() - ts) * 1000, gabriel_msg.index))


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


def process_and_measure_cpu_time(img, app_handler):
    ts = time.time()
    result = app_handler.process(img)
    time_lapse = int(round((time.time() - ts) * 1000))
    return result, time_lapse


def batch_process_multiple(worker_num,
                           video_uri, app,
                           store_result=False, store_latency=False, store_profile=False, trace=None, cpu=None, memory=None):
    """Multiple batch process at the same time. mainly used for profiling.
    Arguments are the same as batch_process, except worker_num.
    """
    procs = [multiprocessing.Process(target=batch_process, args=(
        video_uri, app, store_result, store_latency, store_profile, trace, cpu, memory, worker_num)) for _ in range(worker_num)]
    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


def batch_process(video_uri, app, store_result=False, store_latency=False, store_profile=False, trace=None, cpu=None, memory=None, num_worker=1):
    """Batch process a lego video. Able to store both the result and the frame processing latency.

    Arguments:
        video_uri {[type]} -- [description]
        worker_num: This is just used when store_profile is true. it does not launch multiple processes.
        Use batch_process_multiple to launch multiple workers.

    Keyword Arguments:
        store_result {bool} -- [description] (default: {False})
        store_latency {bool} -- [description] (default: {False})
    """
    app = importlib.import_module(app)
    app_handler = app.Handler()
    vc = client.VideoClient(
        app.__name__, video_uri, None, loop=False, random_start=False)
    sess = None
    if store_result or store_latency or store_profile:
        sess = dbutils.get_session()
    idx = 1
    while True:
        try:
            img = vc.get_frame()
        except ValueError as e:
            logger.error(e)
            logger.info('video ended.')
            break
        result, time_lapse = process_and_measure_cpu_time(img, app_handler)
        logger.debug("[pid: {}] processing frame {} from {}. {} ms".format(os.getpid(),
                                                                           idx, video_uri, int(time_lapse)))
        logger.debug(result)
        if store_result:
            rec, _ = dbutils.get_or_create(
                sess,
                models.SS,
                name=config.EXP,
                index=idx,
                trace=os.path.basename(os.path.dirname(video_uri)))
            rec.val = str(result)
        if store_latency:
            rec, _ = dbutils.get_or_create(
                sess,
                models.LegoLatency,
                name=config.EXP,
                index=idx)
            rec.val = int(time_lapse)
        if store_profile:
            dbutils.insert(
                sess,
                models.ResourceLatency,
                {'trace': trace, 'index': idx, 'name': config.EXP,
                    'cpu': cpu, 'memory': memory,
                    'latency': time_lapse, 'num_worker': num_worker}
            )
        if sess is not None:
            sess.commit()
        idx += 1

    if sess is not None:
        sess.close()


def phash(video_uri):
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    sess = dbutils.get_session()
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
            sess.commit()
        idx += 1
    sess.close()


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
