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
import numpy as np
import os
import select
import socket
import struct
import sys
import threading
import time
import traceback
import config
import Task

from ikea import ikea_cv as ic
from ikea import zhuocv as zc


def reorder_objects(result):
    # build a mapping between faster-rcnn recognized object order to a standard order
    object_mapping = [-1] * len(config.LABELS)
    with open("model/labels.txt") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            line = line.strip()
            object_mapping[idx] = config.LABELS.index(line)

    for i in xrange(result.shape[0]):
        result[i, -1] = object_mapping[int(result[i, -1] + 0.1)]

    return result


class IkeaHandler(object):
    def __init__(self):
        self.is_first_image = True
        self.task = Task.Task()

    def process(self, img):
        if self.is_first_image:
            self.is_first_image = False
            result = self.task.get_instruction(np.array([]))
        else:
            ## preprocessing of input image
            resize_ratio = 1
            if max(img.shape) > config.IMAGE_MAX_WH:
                resize_ratio = float(config.IMAGE_MAX_WH) / max(img.shape[0], img.shape[1])
                img = cv2.resize(img, (0, 0), fx = resize_ratio, fy = resize_ratio, interpolation = cv2.INTER_AREA)

            objects = ic.detect_object(img, resize_ratio)
            objects = reorder_objects(objects)
            result = self.task.get_instruction(objects)

        if 'speech' in result:
            return 'speech: {}'.format(result['speech'])

        return 'None'


def main():
    handler = IkeaHandler()
    cap = cv2.VideoCapture('ikea.mp4')
    ret, frame = cap.read()
    while (cap.isOpened() and ret == True):
        print handler.process(frame)
        ret, frame = cap.read()


if __name__ == '__main__':
    main()
