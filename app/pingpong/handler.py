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
from logzero import logger

from pingpong import config
from pingpong import pingpong_cv as pc
from pingpong import zhuocv as zc

config.setup(is_streaming=True)
display_list = config.DISPLAY_LIST

LOG = logger
LOG_TAG = "Pingpong Server: "


def current_milli_time(): return int(round(time.time() * 1000))


class Trace:
    def __init__(self, n):
        self.trace = []
        self.max_len = n

    def insert(self, item):
        # item is a tuple of (timestamp, data)
        if item[1] is None:  # item is None
            return
        self.trace.append(item)
        if len(self.trace) > self.max_len:
            del self.trace[0]
        while self.trace[-1][0] - self.trace[0][0] > 2000:
            del self.trace[0]

    def is_playing(self, t):
        """Determine if the game is being played.

        The game is being played if there are >=4 record ball data
        within last 2 seconds.

        Arguments:
            t {[type]} -- current timestamp

        Returns:
            [type] -- [description]
        """
        counter = 0
        for item in self.trace:
            if t - item[0] < 2000:
                counter += 1
        return counter >= 4

    def leftOrRight(self):
        # TODO: there should be a better way of doing this
        area_min = 10000
        loc_min = None
        for item in self.trace:
            area, loc = item[1]
            if area < area_min:
                area_min = area
                loc_min = loc
        if loc_min is None:
            return "unknown"
        loc_x = loc_min[0]
        if loc_x < config.O_IMG_WIDTH / 2:
            return "left"
        else:
            return "right"


class PingpongHandler(object):
    def __init__(self):
        super(PingpongHandler, self).__init__()

        self.stop = threading.Event()

        self.prev_frame_info = None
        self.ball_trace = Trace(20)
        self.opponent_x = config.O_IMG_WIDTH / 2
        self.state = {'is_playing': False,
                      'ball_position': "unknown",
                      'opponent_position': "unknown",
                      }

        self.last_played_t = time.time()
        self.last_played = "nothing"

        self.seen_opponent = False

    def __repr__(self):
        return "Pingpong Handler"

    def process(self, img):
        frame_time = current_milli_time()
        self.state['is_playing'] = self.ball_trace.is_playing(
            frame_time) and self.seen_opponent

        # preprocessing of input image
        if max(img.shape) != config.IMAGE_MAX_WH:
            resize_ratio = float(config.IMAGE_MAX_WH) / max(img.shape)
            img = cv2.resize(img, (0, 0), fx=resize_ratio,
                             fy=resize_ratio, interpolation=cv2.INTER_AREA)

        # check if two frames are too close
        ### jjw: removed. as such suppresion can be done on the client
        # if self.prev_frame_info is not None and frame_time - self.prev_frame_info['time'] < 80:
        #     return "two frames too close!"

        # find table
        rtn_msg, objects = pc.find_table(img, display_list)
        if rtn_msg['status'] != 'success':
            return rtn_msg['message']

        img_rotated, mask_table, rotation_matrix = objects
        current_frame_info = {'time': frame_time,
                              'img': img,
                              'img_rotated': img_rotated,
                              'mask_ball': None}

        # in case we don't have good "previous" frame, process the current one and return
        mask_ball = None
        ball_stat = None
        if self.prev_frame_info is None or frame_time - self.prev_frame_info['time'] > 300:
            LOG.info(LOG_TAG + "previous frame not good")
            rtn_msg, objects = pc.find_pingpong(
                img, None, mask_table, None, rotation_matrix, display_list)
            if rtn_msg['status'] != 'success':
                return rtn_msg['message']
            else:
                mask_ball, ball_stat = objects
            self.ball_trace.insert((frame_time, ball_stat))
            current_frame_info['mask_ball'] = mask_ball
            self.prev_frame_info = current_frame_info
            return 'prev_frame marked'

        # now we do have an okay previous frame
        ## jjw: find_pingpong depends on both current frame and previous frame
        rtn_msg, objects = pc.find_pingpong(
            img, self.prev_frame_info['img'], mask_table, self.prev_frame_info['mask_ball'], rotation_matrix, display_list)
        if rtn_msg['status'] != 'success':
            # jjw: the original app doesn't return here
            return rtn_msg['message']
            # LOG.info(LOG_TAG + rtn_msg['message'])
        else:
            mask_ball, ball_stat = objects
        self.ball_trace.insert((frame_time, ball_stat))
        current_frame_info['mask_ball'] = mask_ball

        # determine where the ball was hit to
        self.state['ball_position'] = self.ball_trace.leftOrRight()

        # find position (relatively, left or right) of your opponent
        ## jjw: find_opponent depends on both current frame and previous frame
        rtn_msg, objects = pc.find_opponent(
            img_rotated, self.prev_frame_info['img_rotated'], display_list)
        if rtn_msg['status'] != 'success':
            self.seen_opponent = False
            self.prev_frame_info = current_frame_info
            return rtn_msg['message']
        self.seen_opponent = True
        opponent_x = objects
        # a simple averaging over history
        self.opponent_x = self.opponent_x * 0.7 + opponent_x * 0.3
        self.state['opponent_position'] = "left" if self.opponent_x < config.O_IMG_WIDTH * 0.58 else "right"

        # now user has done something, provide some feedback
        t = time.time()
        if self.state['is_playing']:
            if self.state['opponent_position'] == "left":
                if (t - self.last_played_t < 3 and self.last_played == "right") or (t - self.last_played_t < 1):
                    return 'No instruction. oppo on left, last played right.'
                self.last_played_t = t
                self.last_played = "right"
                return 'inst: right'
            elif self.state['opponent_position'] == "right":
                if (t - self.last_played_t < 3 and self.last_played == "left") or (t - self.last_played_t < 1):
                    return 'No instruction. oppo on right, last played left.'
                self.last_played_t = t
                self.last_played = "left"
                return 'inst: left'
        else:
            return 'idle'
