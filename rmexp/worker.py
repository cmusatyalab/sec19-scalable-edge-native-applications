from __future__ import absolute_import, division, print_function

import json
import logging
import os
import time

import cv2
import face
import fire
import lego
import logzero
import numpy as np
import pingpong
import pool
from logzero import logger
from rmexp import config, cvutils, dbutils, gabriel_pb2
from rmexp.schema import models

logzero.loglevel(logging.DEBUG)


def work_loop(job_queue, app):
    handler = app_to_handler[app]
    sess = dbutils.get_session()
    while True:
        msg = job_queue.get()
        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.ParseFromString(msg)
        encoded_im, ts = gabriel_msg.data, gabriel_msg.timestamp
        encoded_im_np = np.asarray(bytearray(encoded_im), dtype=np.uint8)
        img = cv2.imdecode(encoded_im_np, cv2.CV_LOAD_IMAGE_UNCHANGED)
        result = handler.process(img)
        finished_t = time.time()
        time_lapse = (finished_t - ts) * 1000

        if gabriel_msg.reply:
            reply = gabriel_pb2.Message()
            reply.data = str(result)
            reply.timestamp = gabriel_msg.timestamp
            reply.index = gabriel_msg.index
            job_queue.put(reply.SerializeToString())

        logger.debug(result)
        logger.debug('[proc {}] takes {} ms for frame {}'.format(
            os.getpid(), (time.time() - ts) * 1000, gabriel_msg.index))

        if config.EXP:
            dbutils.insert_or_update_one(
                sess, models.LegoLatency,
                {'name': config.EXP, 'index': gabriel_msg.index},
                {'val': time_lapse, 'finished': finished_t}
            )

            sess.commit()

    sess.close()


apps = {
    'lego': lego,
    'pingpong': pingpong,
    'pool': pool,
    'face': face
}


def get_app_module_from_name(x): return apps[x]


def batch_process(video_uri, app, store_result=False, store_latency=False, store_profile=False, trace=None, cpu=None, memory=None):
    """Batch process a lego video. Able to store both the result and the frame processing latency.

    Arguments:
        video_uri {[type]} -- [description]

    Keyword Arguments:
        store_result {bool} -- [description] (default: {False})
        store_latency {bool} -- [description] (default: {False})
    """
    app = get_app_module_from_name(app)
    app_handler = app.Handler()
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    sess = None
    if store_result or store_latency or store_profile:
        sess = dbutils.get_session()
    idx = 1
    while has_frame:
        has_frame, img = cam.read()
        if img is not None:
            cvutils.resize_to_max_wh(img, app.config.IMAGE_MAX_WH)
            ts = time.time()
            result = app_handler.process(img)
            time_lapse = (time.time() - ts) * 1000
            logger.debug("processing frame {} from {}. {} ms".format(
                idx, video_uri, int(time_lapse)))
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
                dbutils.insert_or_update_one(
                    sess,
                    models.ResourceLatency,
                    {'trace': trace, 'index': idx, 'cpu': cpu, 'memory': memory},
                    {'latency': time_lapse}
                )
            if sess is not None:
                sess.commit()
            logger.debug(result)
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
