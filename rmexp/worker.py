from __future__ import absolute_import, division, print_function

import ast
import logging
import os
import time

import cv2
import fire
import lego
import logzero
import numpy as np
from logzero import logger

from rmexp import config, dbutils
from rmexp.schema import models

logzero.loglevel(logging.DEBUG)


def lego_loop(job_queue):
    lego_app = lego.LegoHandler()
    sess = dbutils.get_session()
    while True:
        _, item = job_queue.get()
        (encoded_im, ts) = ast.literal_eval(item)
        encoded_im_np = np.asarray(bytearray(encoded_im), dtype=np.uint8)
        img = cv2.imdecode(encoded_im_np, cv2.CV_LOAD_IMAGE_UNCHANGED)
        result = lego_app.handle_img(img)
        time_lapse = (time.time() - ts) * 1000
        logger.debug(result)
        logger.debug('[proc {}] takes {} ms for an item'.format(
            os.getpid(), (time.time() - ts) * 1000))
        sess.add(models.LegoLatency(name=config.EXP, val=int(time_lapse)))
        sess.commit()


def batch_process(video_uri):
    lego_app = lego.LegoHandler()
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    sess = dbutils.get_session()
    while has_frame:
        ts = time.time()
        has_frame, img = cam.read()
        if img is not None:
            result = lego_app.handle_img(img)
            time_lapse = (time.time() - ts) * 1000
            sess.add(models.LegoLatency(name=config.EXP, val=int(time_lapse)))
            sess.commit()
            logger.debug(result)


if __name__ == "__main__":
    fire.Fire()
