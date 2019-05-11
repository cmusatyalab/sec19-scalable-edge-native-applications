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

# Port for communication between proxy and task server
TASK_SERVER_IP = "128.2.209.93"
TASK_SERVER_PORT = 5554

# Engine info
ENGINE_ID_LIST = ['FACE_DLIB', 'openface', 'LBPH', 'eigen',
                  'FACE_FISHER', 'LBPH_haar', 'eigen_haar', 'FACE_FISHER_HAAR']
BEST_ENGINE = 'FACE_DLIB'
CHECK_ALGORITHM = "table"
CHECK_LAST_TH = 1

# Port for communication between master and workder proxies
MASTER_SERVER_PORT = 5555

# Max image width and height
IMAGE_MAX_WH = 640

# Display
DISPLAY_MAX_PIXEL = 640
DISPLAY_SCALE = 1
DISPLAY_LIST_ALL = ['input']
DISPLAY_LIST_TEST = ['input']
DISPLAY_LIST_STREAM = []
DISPLAY_LIST_TASK = []

# Used for cvWaitKey
DISPLAY_WAIT_TIME = 1 if IS_STREAMING else 500


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
