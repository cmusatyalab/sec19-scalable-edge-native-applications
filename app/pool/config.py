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

# If True, configurations are set to process video stream in real-time (use with proxy.py)
# If False, configurations are set to process one independent image (use with img.py)
IS_STREAMING = True

# Pure state detection or generate feedback as well
RECOGNIZE_ONLY = True

# Whether or not to save the displayed image in a temporary directory
SAVE_IMAGE = False

# Max image width and height
IMAGE_MAX_WH = 1920

# Display
DISPLAY_MAX_PIXEL = 640
DISPLAY_SCALE = 5
DISPLAY_LIST_ALL = ['input', 'blue', 'bluer', 'table', 'table_convex', 'interesting', 'balls', 'CO_balls', 'pocket', 'cue']
DISPLAY_LIST_TEST = ['input', 'table', 'blue', 'interesting', 'cue', 'balls', 'CO_balls', 'pocket']
DISPLAY_LIST_STREAM = []
DISPLAY_LIST_TASK = []

# Used for cvWaitKey
DISPLAY_WAIT_TIME = 1 if IS_STREAMING else 500

# Randomly add good words before each instruction
GOOD_WORDS = ["Excellent. ", "Great. ", "Good job. ", "Wonderful. "]

def setup(is_streaming):
    global IS_STREAMING, DISPLAY_LIST, DISPLAY_WAIT_TIME, SAVE_IMAGE
    IS_STREAMING = is_streaming
    if not IS_STREAMING:
        DISPLAY_LIST = DISPLAY_LIST_TEST
    else:
        if RECOGNIZE_ONLY:
            DISPLAY_LIST = DISPLAY_LIST_STREAM
        else:
            DISPLAY_LIST = DISPLAY_LIST_TASK
    DISPLAY_WAIT_TIME = 1 if IS_STREAMING else 500
    SAVE_IMAGE = not IS_STREAMING

