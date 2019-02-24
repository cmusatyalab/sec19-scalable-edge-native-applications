#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

import collections

import cv2
import fire

from lego import lego
from utils import timeit
from logzero import logger

time_log = collections.defaultdict(list)


@timeit(time_log)
def process_request(lego_app, img):
    result = lego_app.handle_img(img)
    logger.debug(result)


def main(video_uri):
    lego_app = lego.LegoHandler()
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    while has_frame:
        has_frame, img = cam.read()
        if img is not None:
            process_request(lego_app, img)
    logger.info(time_log)


if __name__ == "__main__":
    fire.Fire(main)
