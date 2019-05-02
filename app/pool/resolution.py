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
# This script is used for testing computer vision algorithms in the
# Lego Task Assistance project. It does processing for one image.
# Usage: python img.py <image-path>
#

'''
This script loads a single image from file, and tries to generate relevant information of Pool Assistant.
It is primarily used as a quick test tool for the computer vision algorithm.
'''

import argparse
import cv2
import os
import sys
import time

sys.path.insert(0, "..")
import config
import pool_cv as pc
import zhuocv as zc

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder",
                        help = "The folder to images to process",
                       )
    args = parser.parse_args()
    return (args.input_folder)

# load test image
input_folder = parse_arguments()
resolution_list = [180, 360, 720, 1080]
data_folder = {180: 'pool-180p', 360: 'pool', 720: 'pool-720p', 1080: 'pool-1080p'}
right = {}
wrong = {}
right_all = {}
wrong_all = {}
for res in resolution_list:
    right[res] = 0
    wrong[res] = 0
    right_all[res] = 0
    wrong_all[res] = 0

groundtruth_folder = os.path.join(input_folder, data_folder[1080])
filelist = [os.path.join(groundtruth_folder, f) for f in os.listdir(groundtruth_folder)
        if f.lower().endswith("jpeg") or f.lower().endswith("jpg") or f.lower().endswith("bmp")]
filelist.sort()

counter = 0
for f in filelist:
    counter += 1
    print '\n'
    print f
    img = cv2.imread(f)
    rtn_msg, objects_truth = pc.process(img, [])
    if objects_truth is not None:
        cue_truth, CO_balls_truth, pocket_truth = objects_truth
        response_truth = pc.get_guidance(img, cue_truth, CO_balls_truth, pocket_truth, [])
    else:
        response_truth = None
    for res in resolution_list:
        if res == 1080:
            continue
        img = cv2.imread(f.replace(data_folder[1080], data_folder[res]))
        rtn_msg, objects = pc.process(img, [])
        if objects is not None:
            cue, CO_balls, pocket = objects
            response = pc.get_guidance(img, cue, CO_balls, pocket, [])
        else:
            response = None

        if response == response_truth:
            right_all[res] += 1
            if response_truth is not None:
                right[res] += 1
        else:
            wrong_all[res] += 1
            if response_truth is not None:
                print objects_truth
                print objects
                wrong[res] += 1
    print right, wrong, right_all, wrong_all

