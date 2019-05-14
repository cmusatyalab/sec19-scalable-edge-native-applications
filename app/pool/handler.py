#!/usr/bin/env python
#
# Cloudlet Infrastructure for Mobile Computing
#   - Task Assistance
#
#   Author: Zhuo Chen <zhuoc@cs.cmu.edu>
#
#   Copyright (C) 2011-2013 Carnegie Mellon University
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import cv2
import json
import multiprocessing
import os
import pprint
import Queue
import sys
import threading
import time

from pool import zhuocv as zc
from pool import pool_cv as pc


IMAGE_MAX_WH = 1920


class PoolHandler(object):
    def __repr__(self):
        return "Pool Handler"

    def process(self, img):
        if max(img.shape) > IMAGE_MAX_WH:
            resize_ratio = (float(IMAGE_MAX_WH) /
                max(img.shape[0], img.shape[1]))
            img = cv2.resize(img, (0, 0), fx=resize_ratio,
                             fy=resize_ratio, interpolation=cv2.INTER_AREA)

        # process the image
        rtn_msg, objects = pc.process(img)

        if rtn_msg['status'] == 'success':
            cue, CO_balls, pocket = objects
            speech = pc.get_guidance(img, cue, CO_balls, pocket)
            return 'speech: {}'.format(speech)

        return rtn_msg['message']


def main():
    handler = PoolHandler()
    cap = cv2.VideoCapture('pool.mp4')
    ret, frame = cap.read()
    while (cap.isOpened() and ret == True):
        print(handler.process(frame))
        ret, frame = cap.read()


if __name__ == '__main__':
    main()
