from __future__ import absolute_import, division, print_function

import os
import time

import cv2
from logzero import logger
from rmexp import gabriel_pb2
from twisted.internet import reactor, task


class VideoClient(object):
    def __init__(self, video_uri, network_connector, video_params=None):
        super(VideoClient, self).__init__()
        self._fid = 0
        self._cam = self.get_video_capture(video_uri)
        if video_params is not None:
            self._set_cam_params(video_params['width'], video_params['height'])
        self._nc = network_connector

    def send_frame(self, frame, *args, **kwargs):
        frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.data = frame_bytes
        gabriel_msg.timestamp = time.time()
        gabriel_msg.index = '{}-{}'.format(os.getpid(), self._fid)
        self._nc.put(gabriel_msg.SerializeToString())
        self._fid += 1

    def get_frame(self):
        has_frame, img = self._cam.read()
        if has_frame and img is not None:
            logger.debug('[proc {}] acquired a frame of size: {}'.format(
                os.getpid(), img.shape))
            return img
        else:
            self._cam.release()
            reactor.callFromThread(reactor.stop)
            raise ValueError("Failed to get another frame.")

    def get_and_send_frame(self, filter_func=None, *args, **kwargs):
        frame = self.get_frame()
        if filter_func is None or filter_func(frame):
            self.send_frame(frame, self._nc, *args, **kwargs)

    def get_video_capture(self, uri):
        cam = cv2.VideoCapture(uri)
        return cam

    def _set_cam_params(self, width, height):
        self._cam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, width)
        self._cam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, height)
