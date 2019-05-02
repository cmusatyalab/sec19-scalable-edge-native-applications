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
import numpy as np
import os
import sys
import time

sys.path.insert(0, "..")
import config
import zhuocv as zc

current_milli_time = lambda: int(round(time.time() * 1000))


#############################################################
def set_config(is_streaming):
    config.setup(is_streaming)

def _detect_table(img, display_list):
    SE1 = int(float(img.shape[1]) / 640 * 5 + 0.5)
    DOB_PARA = int(float(img.shape[1]) / 640 * 51 + 0.5)
    ## detect blue/purple table
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask_blue = zc.color_inrange(img, 'HSV', hsv = hsv, H_L = 88, H_U = 125, S_L = 120, V_L = 100)
    mask_blue = zc.expand(mask_blue, SE1)
    mask_table, _ = zc.find_largest_CC(mask_blue)
    if mask_table is None:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find table'}
        return (rtn_msg, None)
    mask_blue = zc.shrink(mask_blue, SE1)

    # revise table detection based on how blue the current table is
    table_hsv_ave = np.mean(hsv[mask_blue.astype(bool)], axis = 0)
    mask_blue = zc.color_inrange(img, 'HSV', hsv = hsv, H_L = table_hsv_ave[0] - 15, H_U = table_hsv_ave[0] + 15, S_L = min(120, table_hsv_ave[1] - 30), V_L = min(80, table_hsv_ave[2] - 50))
    #mask_blue = cv2.morphologyEx(mask_blue, cv2.MORPH_OPEN, zc.generate_kernel(3, 'square'), iterations = 2)
    mask_table, _ = zc.find_largest_CC(mask_blue)
    if mask_table is None:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find table'}
        return (rtn_msg, None)
    mask_table_fat, _ = zc.find_largest_CC(zc.expand(mask_blue, SE1, iterations = 2))
    mask_table_fat = zc.shrink(mask_table_fat, SE1, iterations = 2)

    zc.check_and_display_mask("blue", img, mask_blue, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)
    zc.check_and_display_mask("table", img, mask_table, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)


    ## detect the part that is bluer than neighbors, which is likely table edge
    blue_dist = zc.color_dist(img, 'HSV', HSV_ref = table_hsv_ave, useV = False)
    blue_DoB = zc.get_DoB(blue_dist, DOB_PARA, 1, method = 'Average')
    mask_bluer = zc.color_inrange(blue_DoB, 'single', L = 20)
    zc.check_and_display_mask("bluer", img, mask_bluer, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    rtn_msg = {'status' : 'success'}
    return (rtn_msg, (mask_blue, mask_bluer, mask_table, mask_table_fat))

def _detect_balls(img, mask_tables, display_list):
    SE1 = int(float(img.shape[1]) / 640 * 3 + 0.5)
    SE2 = int(float(img.shape[1]) / 640 * 5 + 0.5)
    mask_blue, mask_bluer, mask_table, mask_table_fat = mask_tables

    balls = []
    mask_blue = zc.expand(mask_blue, SE1, iterations = 2)
    mask_balls = np.zeros(mask_blue.shape, dtype = np.uint8)
    ## find all the holes
    contours, hierarchy = cv2.findContours(mask_blue, mode = cv2.RETR_CCOMP, method = cv2.CHAIN_APPROX_NONE)
    for cnt_idx, cnt in enumerate(contours):
        if hierarchy[0, cnt_idx, 3] != -1 and cv2.contourArea(cnt) > img.shape[1] / 16:
            cv2.drawContours(mask_balls, contours, cnt_idx, 255, -1)
    mask_table_convex, _ = zc.make_convex(mask_table.copy(), use_approxPolyDp = False)
    mask_balls = cv2.bitwise_and(mask_balls, mask_table_convex)

    ## use circles to approximate the balls
    mask_balls = zc.expand(mask_balls, SE2, iterations = 2)
    contours, hierarchy = cv2.findContours(mask_balls.copy(), mode = cv2.RETR_CCOMP, method = cv2.CHAIN_APPROX_NONE)
    for cnt_idx, cnt in enumerate(contours):
        center, radius = cv2.minEnclosingCircle(cnt)
        balls.append((center, radius))
        cv2.circle(mask_balls, (int(center[0]), int(center[1])), int(radius), 255, -1)

    zc.check_and_display_mask("balls", img, mask_balls, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    rtn_msg = {'status' : 'success'}
    return (rtn_msg, (balls, mask_balls))

def _detect_cue(img, mask_tables, mask_balls, display_list):
    CUE_MIN_LENGTH = int(float(img.shape[1]) / 640 * 40 + 0.5)
    PARA1 = int(float(img.shape[1]) / 640 * 2 + 0.5)
    mask_blue, mask_bluer, mask_table, mask_table_fat = mask_tables

    ### edges on the table
    #img_table = np.zeros(img.shape, dtype=np.uint8)
    #img_table = cv2.bitwise_and(img, img, dst = img_table, mask = mask_table_convex)
    #bw_table = cv2.cvtColor(img_table, cv2.COLOR_BGR2GRAY)
    #edge_table = cv2.Canny(bw_table, 80, 160)
    #edge_table = zc.expand(edge_table, 2)
    #zc.check_and_display("edge_table", edge_table, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    ### detect cue
    #lines = cv2.HoughLinesP(edge_table, 1, np.pi/180, 30, minLineLength = 70, maxLineGap = 3)
    #if lines is None:
    #    rtn_msg = {'status': 'fail', 'message' : 'Cannot find cue'}
    #    return (rtn_msg, None)
    #lines = lines[0]
    #if 'cue_edge' in display_list:
    #    img_cue = img.copy()
    #    for line in lines:
    #        pt1 = (line[0], line[1])
    #        pt2 = (line[2], line[3])
    #        cv2.line(img_cue, pt1, pt2, (255, 0, 255), 2)
    #    zc.check_and_display("cue_edge", img_cue, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    ## interesting parts on the table (pockets, cue, hand, etc.)
    mask_table_convex, _ = zc.make_convex(mask_table.copy(), use_approxPolyDp = False)
    zc.check_and_display_mask("table_convex", img, mask_table_convex, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)
    mask_interesting = cv2.subtract(cv2.subtract(mask_table_convex, mask_table), mask_bluer)
    mask_interesting = cv2.subtract(mask_interesting, mask_balls)
    mask_interesting = zc.shrink(mask_interesting, PARA1)
    zc.check_and_display_mask("interesting", img, mask_interesting, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)
    # find the blob with cue (and probably hand)
    # TODO: this may be more robust with find_largest_CC function, in the case of half ball close to the bottom
    mask_cue_hand = zc.get_closest_blob(mask_interesting.copy(), (img.shape[0], img.shape[1] / 2), min_length = CUE_MIN_LENGTH, hierarchy_req = 'outer') # cue must be close to the bottom

    ## find cue top
    p_cue_top = zc.get_edge_point(mask_cue_hand, (0, -1))
    if p_cue_top is None:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find cue top'}
        return (rtn_msg, None)

    ## find cue bottom
    # the cue detected initially may not have reached the bottom of the image
    for i in xrange(10):
        mask_cue_hand = zc.expand_with_bound(mask_cue_hand, cv2.bitwise_not(mask_bluer))
    mask_cue_bottom = mask_cue_hand.copy()
    mask_cue_bottom[:-2, :] = 0
    mask_cue_bottom[:, :p_cue_top[0] - 40] = 0
    mask_cue_bottom[:, p_cue_top[0] + 40:] = 0
    nonzero = np.nonzero(mask_cue_bottom)
    if len(nonzero) < 2 or len(nonzero[0]) == 0:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find cue bottom'}
        return (rtn_msg, None)
    rows, cols = nonzero
    p_cue_bottom = ((np.min(cols) + np.max(cols)) / 2, img.shape[0])

    ## cue info
    cue_length = zc.euc_dist(p_cue_top, p_cue_bottom)
    if 'cue' in display_list:
        img_cue = img.copy()
        img_cue[mask_cue_hand > 0, :] = [0, 255, 255]
        cv2.circle(img_cue, p_cue_top, 3, (255, 0, 255), -1)
        cv2.line(img_cue, p_cue_top, p_cue_bottom, (255, 0, 255), 2)
        zc.display_image("cue", img_cue, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    ## skeletonize
    #skeleton_cue_hand = zc.skeletonize(mask_cue_hand)
    rtn_msg = {'status' : 'success'}
    return (rtn_msg, (p_cue_top, p_cue_bottom, cue_length))

def _detect_CO_balls(img, balls, cue, display_list):
    PARA1 = int(float(img.shape[1]) / 640 * 15 + 0.5)
    PARA2 = int(float(img.shape[1]) / 640 * 40 + 0.5)
    p_cue_top, p_cue_bottom, cue_length = cue

    ## determine which ball is cue ball
    min_dist2cue_top = img.shape[0] + 1
    cue_ball_idx = -1
    for idx, ball in enumerate(balls):
        center, radius = ball
        dist2cue = zc.calc_triangle_area(center, p_cue_top, p_cue_bottom) * 2 / cue_length
        if dist2cue < PARA1:
            dist2cue_top = zc.euc_dist(center, p_cue_top)
            if dist2cue_top < min_dist2cue_top:
                min_dist2cue_top = dist2cue_top
                cue_ball_idx = idx
    if cue_ball_idx == -1:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find cue ball'}
        return (rtn_msg, None)
    cue_ball = balls[cue_ball_idx]

    ## determine which ball is object ball
    min_dist2cue_top = img.shape[0] + 1
    object_ball_idx = -1
    for idx, ball in enumerate(balls):
        if idx == cue_ball_idx:
            continue
        center, radius = ball
        dist2cue = zc.calc_triangle_area(center, p_cue_top, p_cue_bottom) * 2 / cue_length
        if dist2cue < PARA2:
            dist2cue_top = zc.euc_dist(center, p_cue_top)
            if dist2cue_top < min_dist2cue_top:
                min_dist2cue_top = dist2cue_top
                object_ball_idx = idx
    if object_ball_idx == -1:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find object ball'}
        return (rtn_msg, None)
    object_ball = balls[object_ball_idx]

    if 'CO_balls' in display_list:
        img_balls = img.copy()
        cv2.circle(img_balls, (int(cue_ball[0][0]), int(cue_ball[0][1])), int(cue_ball[1]), (255, 255, 255), -1)
        cv2.circle(img_balls, (int(object_ball[0][0]), int(object_ball[0][1])), int(object_ball[1]), (0, 0, 255), -1)
        zc.display_image("CO_balls", img_balls, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    rtn_msg = {'status' : 'success'}
    return (rtn_msg, (cue_ball, object_ball))

def _detect_pocket(img, mask_tables, cue, display_list):
    PARA1 = int(float(img.shape[1]) / 640 * 2 + 0.5)
    mask_blue, mask_bluer, mask_table, mask_table_fat = mask_tables
    p_cue_top, p_cue_bottom, cue_length = cue

    mask_table_convex, _ = zc.make_convex(mask_table_fat.copy(), use_approxPolyDp = False)
    mask_pocket = cv2.subtract(cv2.subtract(mask_table_convex, mask_table_fat), mask_bluer)
    mask_pocket = zc.shrink(mask_pocket, PARA1)
    mask_pocket[p_cue_top[1] - 5:, :] = 0
    zc.check_and_display_mask("pocket", img, mask_pocket, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)
    contours, hierarchy = cv2.findContours(mask_pocket, mode = cv2.RETR_CCOMP, method = cv2.CHAIN_APPROX_NONE)
    pocket = None
    cnt_pocket = None
    min_dist2cue = img.shape[0] + 1
    for cnt_idx, cnt in enumerate(contours):
        pocket_center = zc.get_contour_center(cnt)
        dist2cue = zc.calc_triangle_area(pocket_center, p_cue_top, p_cue_bottom) * 2 / cue_length
        if dist2cue < min_dist2cue:
            min_dist2cue = dist2cue
            pocket = pocket_center
            cnt_pocket = cnt
    if pocket is None:
        rtn_msg = {'status': 'fail', 'message' : 'Cannot find pocket'}
        return (rtn_msg, None)

    rtn_msg = {'status' : 'success'}
    return (rtn_msg, (pocket, cnt_pocket))


def _detect_aim_point(cue, CO_balls, pocket):
    def _angle2fraction(angle):
        '''
        Calculcate desired fraction of overlap from angle according to fraction aiming system
        Reference: http://billiards.colostate.edu/threads/aiming.html, https://youtu.be/2kuJTwQ1M9k
        '''
        if angle > 48.6: # very thin
            return (90 - angle) / 41.4 * 0.25
        elif angle > 30: # thin
            return (48.6 - angle) / 28.6 * 0.25 + 0.25
        elif angle > 14.5: # thick
            return (30 - angle) / 15.5 * 0.25 + 0.5
        else: # very thick
            return 1 - angle / 14.5 * 0.25
        return None

    p_cue_top, p_cue_bottom, cue_length = cue
    cue_ball, object_ball = CO_balls

    ## calculate where to aim based on fractional aiming technique
    p_aim = object_ball[0] # set initial aim point to object ball center
    # because the angle should be angle between pocket-to-OB line and aim line, but not CTC (center to center) line,
    # we need to iterate several times to get the correct fraction
    for iteration in xrange(3): # 3 is an arbitrary number here
        dist_pocket2aim_line = zc.calc_triangle_area(cue_ball[0], p_aim, pocket) * 2 / zc.euc_dist(cue_ball[0], p_aim)
        dist_pocket2aim_point = zc.euc_dist(p_aim, pocket)
        angle = np.arcsin(dist_pocket2aim_line / dist_pocket2aim_point)
        angle = angle / 1.8 # adjust angle because user is not looking straight down. This adjustment is very rough
        angle = angle / np.pi * 180 # convert to degrees

        fraction = _angle2fraction(angle)
        if pocket[0] < object_ball[0][0]: # cut to left
            p_aim = (object_ball[0][0] + (1 - fraction) * object_ball[1] * 2, object_ball[0][1])
        else: # cut to right
            p_aim = (object_ball[0][0] - (1 - fraction) * object_ball[1] * 2, object_ball[0][1])

    ## calculate where is aimed
    p_aimed = ((object_ball[0][1] - cue_ball[0][1]) / (cue_ball[0][1] - p_cue_bottom[1]) * (cue_ball[0][0] - p_cue_bottom[0]) + cue_ball[0][0], object_ball[0][1])

    rtn_msg = {'status' : 'success'}
    return (rtn_msg, (p_aim, p_aimed))

def process(img, display_list):
    rtn_msg, objects = _detect_table(img, display_list)
    if objects is not None:
        mask_tables = objects
    if rtn_msg['status'] == 'success':
        rtn_msg, objects = _detect_balls(img, mask_tables, display_list)
        if objects is not None:
            balls, mask_balls = objects
    if rtn_msg['status'] == 'success':
        rtn_msg, objects = _detect_cue(img, mask_tables, mask_balls, display_list)
        if objects is not None:
            cue = objects
    if rtn_msg['status'] == 'success':
        rtn_msg, objects = _detect_CO_balls(img, balls, cue, display_list)
        if objects is not None:
            CO_balls = objects
    if rtn_msg['status'] == 'success':
        rtn_msg, objects = _detect_pocket(img, mask_tables, cue, display_list)
        if objects is not None:
            pocket, cnt_pocket = objects
    if rtn_msg['status'] == 'success':
        return (rtn_msg, (cue, CO_balls, pocket))
    else:
        return (rtn_msg, None)

def get_guidance(img, cue, CO_balls, pocket, display_list):
    PARA = int(float(img.shape[1]) / 640 * 8 + 0.5)
    rtn_msg, objects = _detect_aim_point(cue, CO_balls, pocket)
    if objects is not None:
        p_aim, p_aimed = objects
        print objects

    if rtn_msg['status'] == 'success':
        if 'all' in display_list:
            img_display = img.copy()
            # draw balls
            cue_ball, object_ball = CO_balls
            cv2.circle(img_display, (int(cue_ball[0][0]), int(cue_ball[0][1])), int(cue_ball[1]), (255, 255, 255), -1)
            cv2.circle(img_display, (int(object_ball[0][0]), int(object_ball[0][1])), int(object_ball[1]), (0, 0, 255), -1)
            # draw cue
            p_cue_top, p_cue_bottom, _ = cue
            cv2.circle(img_display, p_cue_top, 3, (200, 0, 200), -1)
            cv2.line(img_display, p_cue_top, p_cue_bottom, (200, 0, 200), 3)
            # draw pocket
            cv2.drawContours(img_display, [cnt_pocket], 0, (255, 0, 0), -1)
            # draw aim point
            cv2.circle(img_display, (int(p_aim[0]), int(p_aim[1])), 3, (0, 255, 0), -1)
            # draw aimed point
            cv2.circle(img_display, (int(p_aimed[0]), int(p_aim[1])), 3, (0, 0, 0), -1)
            zc.display_image("all", img_display, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

    if rtn_msg['status'] == 'success':
        if abs(p_aim[0] - p_aimed[0]) < PARA:
            return "good"
        elif p_aim[0] < p_aimed[0]:
            return "left"
        else:
            return "right"
    else:
        return None
