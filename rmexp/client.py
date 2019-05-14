from __future__ import absolute_import, division, print_function

import os
import time
import types

import cv2
from logzero import logger
from rmexp import gabriel_pb2, cvutils
from twisted.internet import reactor, task


class VideoClient(object):
    def __init__(self, video_uri, network_connector, video_params=None, max_wh=None, loop=False):
        super(VideoClient, self).__init__()
        self._fid = 0
        self._cam = self.get_video_capture(video_uri)
        self._nc = network_connector
        self._max_wh = max_wh
        self._loop = loop
        if video_params is not None:
            self._set_cam_params(video_params)

    def send_frame(self, frame, frame_id, reply, **kwargs):
        frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.data = frame_bytes
        gabriel_msg.timestamp = kwargs['time']
        gabriel_msg.index = '{}-{}'.format(os.getpid(), frame_id)
        gabriel_msg.reply = reply
        self._nc.put([gabriel_msg.SerializeToString(), ],
                     service=kwargs['app'])

    def get_frame(self):
        """Public function to get a frame.
        Internally, invoke _get_frame_and_resize to get a correct sized frame
        """
        has_frame, img = self._get_frame_and_resize()
        if has_frame and img is not None:
            logger.debug('[proc {}] acquired a frame of size: {}'.format(
                os.getpid(), img.shape))
            self._fid += 1
            return img
        else:
            self._cam.release()
            reactor.callFromThread(reactor.stop)
            raise ValueError("Failed to get another frame.")

    def get_and_send_frame(self, filter_func=None, reply=False, **kwargs):
        """Public convenient function to get and send a frame."""
        frame = self.get_frame()
        ts = time.time()
        if filter_func is None or filter_func(frame):
            self.send_frame(frame, self._fid, reply=reply, time=ts, **kwargs)

    def _get_frame_and_resize(self):
        has_frame, img = self._cam.read()
        # reset video for looping
        if img is None and self._loop:
            self._cam.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, 0)
            has_frame, img = self._cam.read()

        if img is not None and self._max_wh is not None:
            img = cvutils.resize_to_max_wh(img, self._max_wh)
        return has_frame, img

    def get_video_capture(self, uri):
        cam = cv2.VideoCapture(uri)
        return cam

    def _set_cam_params(self, video_params):
        if 'width' in video_params:
            self._cam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,
                          video_params['width'])
        if 'height' in video_params:
            self._cam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,
                          video_params['height'])


class RTVideoClient(VideoClient):

    def __init__(self, *args, **kwargs):
        super(RTVideoClient, self).__init__(*args, **kwargs)
        self._start_time = None
        self._fps = 30  # self._cam.get(cv2.cv.CV_CAP_PROP_FPS)
        logger.debug("FPS={}".format(self._fps))

    def start(self):
        self._start_time = time.time()

    def get_frame(self):
        expected_frame_id = int(
            self._fps * (time.time() - self._start_time)) + 1

        while expected_frame_id <= self._fid:
            # too soon, block until at least next frame
            time.sleep(0.030)
            expected_frame_id = int(
                self._fps * (time.time() - self._start_time)) + 1

        # fast-forward
        for _ in range(expected_frame_id - self._fid):
            has_frame, img = self._get_frame_and_resize()
            if has_frame and img is not None:
                pass
            else:
                self._cam.release()
                raise ValueError("Failed to get another frame.")

        logger.debug('image size: {}'.format(img.shape))
        self._fid = expected_frame_id
        logger.debug('[proc {}] RTVideoClient acquired frame id {} of size: {}'.format(
            os.getpid(), self._fid, img.shape))
        return img


if __name__ == "__main__":
    video_uri = 'data/lego-trace/1/video.mp4'
    vc = RTVideoClient(video_uri, None)
    idx = 0
    while True:
        idx += 1
        has_frame, img = vc.get_frame_and_resize()
        logger.debug(idx)
        assert img is not None
