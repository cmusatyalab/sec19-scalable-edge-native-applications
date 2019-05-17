from __future__ import absolute_import, division, print_function

import os
import time
import types
import random

import cv2
from logzero import logger
from rmexp import gabriel_pb2, cvutils
from twisted.internet import reactor, task


class VideoClient(object):
    def __init__(self, app, video_uri,
                 network_connector=None, video_params=None, max_wh=None,
                 loop=False, random_start=False):
        super(VideoClient, self).__init__()
        self._cam = self.get_video_capture(video_uri)
        self._fps = self._cam.get(cv2.cv.CV_CAP_PROP_FPS)
        self._start_fid = 0
        # fid represents the frame id that is sampled
        # when loop is true, this number can be larger than
        # self._cam_frame_cnt
        self._fid = None
        self._max_wh = max_wh
        self._loop = loop
        self._app = app
        self._nc = network_connector
        assert self._app in ['lego', 'pingpong', 'face',
                             'pool', 'ikea'], 'Unknown app: {}'.format(self._app)

        # configure the cam
        self._cam_frame_cnt = int(
            self._cam.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        if random_start:
            self._start_fid = random.randint(0, self._cam_frame_cnt - 1)
        self._set_cam_pos(self._start_fid)
        if video_params is not None:
            self._set_cam_params(video_params)
        assert self._fid is not None, 'Camera position needs to be initialized using _set_cam_pos'
        logger.info('initialized a video client. video_uri: {}, video_params: {}, loop: {},\
                    start_fid: {}, total frame_cnt: {}, fps: {}'.format(
            video_uri,
            video_params,
            self._loop,
            self._start_fid,
            self._cam_frame_cnt,
            self._fps
        ))

    def _set_cam_pos(self, fid):
        self._cam.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, fid % self._cam_frame_cnt)
        self._fid = fid

    def send_frame(self, frame, frame_id, reply, **kwargs):
        frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.data = frame_bytes
        gabriel_msg.timestamp = kwargs['time']
        gabriel_msg.index = '{}-{}'.format(os.getpid(), frame_id)
        gabriel_msg.reply = reply
        self._nc.put([gabriel_msg.SerializeToString(), ],
                     service=self._app)

    def get_frame(self):
        """Public function to get a frame.
        Internally, invoke _get_frame_and_resize to get a correct sized frame
        """
        has_frame, img = self._get_frame_and_resize()
        if has_frame and img is not None:
            logger.debug('[proc {}] acquired a frame of size: {}'.format(
                os.getpid(), img.shape))
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
            self.send_frame(frame, self._fid - 1,
                            reply=reply, time=ts, **kwargs)

    def process_reply(self, msg):
        logger.warning('{} reply ignored'.format(self))

    def _get_frame_and_resize(self):
        has_frame, img = self._cam.read()
        # reset video for looping
        if img is None and self._loop:
            self._cam.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, 0)
            has_frame, img = self._cam.read()

        if img is not None and self._max_wh is not None:
            img = cvutils.resize_to_max_wh(img, self._max_wh)

        self._fid += 1
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

    @property
    def current_fid(self):
        """Represents the last frame number read.
        This can be used to query other sensors based on idx
        This is a number between [0, self._cam_frame_cnt - 1]
        """
        return (self._fid - 1) % self._cam_frame_cnt


class RTVideoClient(VideoClient):

    def __init__(self, *args, **kwargs):
        super(RTVideoClient, self).__init__(*args, **kwargs)
        self._start_time = None
        self._fps = 30
        logger.info('RTVideoClient considers FPS to be {}'.format(self._fps))

    def get_frame(self):
        if self._fid == self._start_fid:
            has_frame, img = self._get_frame_and_resize()
            self._start_time = time.time()
            if not has_frame or img is None:
                self._cam.release()
                raise ValueError("Failed to get another frame.")
        else:
            # _fid starts with 0 and represents next available frame
            next_fid = self._fps * \
                (time.time() - self._start_time) + self._start_fid
            next_fid = int(next_fid) if next_fid - \
                int(next_fid) < 10e-3 else int(next_fid) + 1

            # the get_frame is request too soon.
            # current frame has already sampled. need to block and sleep
            if next_fid < self._fid:
                sleep_time = self._start_time + self._fid * \
                    (1. / self._fps) - time.time()
                time.sleep(sleep_time)
                next_fid = self._fid

            # fast-forward
            self._set_cam_pos(next_fid)
            has_frame, img = self._get_frame_and_resize()
            if not has_frame or img is None:
                self._cam.release()
                raise ValueError("Failed to get another frame.")

        logger.debug('[proc {}] RTVideoClient acquired frame id {} pos {} of size: {}'.format(
            os.getpid(), self._fid - 1, self.current_fid, img.shape))
        return img


if __name__ == "__main__":
    video_uri = 'data/lego-trace/1/video.mp4'
    vc = RTVideoClient('lego', video_uri, None)
    idx = 0
    while True:
        idx += 1
        img = vc.get_frame()
        logger.debug(idx)
        assert img is not None
