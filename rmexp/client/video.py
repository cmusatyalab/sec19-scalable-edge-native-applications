from __future__ import absolute_import, division, print_function

import os
import time
import types
import random
import glob

import cv2
import logging
import logzero
from logzero import logger
from rmexp import gabriel_pb2, cvutils

logzero.formatter(logzero.LogFormatter(
    fmt='%(color)s[%(levelname)1.1s %(asctime)s.%(msecs)03d %(module)s:%(lineno)d]%(end_color)s %(message)s'))

logzero.loglevel(logging.DEBUG)


class VideoClient(object):
    def __init__(self, app, video_uri,
                 network_connector=None, video_params=None, max_wh=None,
                 loop=False, random_start=False):
        super(VideoClient, self).__init__()
        self.video_uri = video_uri
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

    def send_frame(self, frame_bytes, frame_id, reply, **kwargs):
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
            return img
        else:
            self._cam.release()
            raise ValueError("Failed to get another frame.")

    def get_and_send_frame(self, filter_func=None, reply=False, **kwargs):
        """Public convenient function to get and send a frame."""
        frame = self.get_frame()
        frame_bytes = cv2.imencode('.jpg', frame)[1].tostring()
        ts = time.time()
        if filter_func is None or filter_func(frame_bytes):
            self.send_frame(frame_bytes, self._fid - 1,
                            reply=reply, time=ts, **kwargs)

    def process_reply(self, msg):
        # logger.trace('{} reply ignored'.format(self))
        pass

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
        tic = time.time()
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
            next_fid = int(next_fid)

            # the get_frame is request too soon.
            # current frame has already sampled. need to block and sleep
            if next_fid < self._fid:
                sleep_time = self._start_time + self._fid * \
                    (1. / self._fps) - time.time()
                logger.debug("Going to sleep {} for frame {}".format(
                    sleep_time, self._fid))
                time.sleep(sleep_time)
                next_fid = self._fid

            # fast-forward
            for _ in range(next_fid + 1 - self._fid):
                has_frame, img = self._get_frame_and_resize()
                if has_frame and img is not None:
                    pass
                else:
                    self._cam.release()
                    raise ValueError("Failed to get another frame.")

            logger.debug("get_frame_and_resize: {}".format(time.time() - tic))

            # # self._set_cam_pos(next_fid) #  this takes 50 ms. WTH?!
            # has_frame, img = self._get_frame_and_resize()
            # self._fid = next_fid

            if not has_frame or img is None:
                self._cam.release()
                raise ValueError("Failed to get another frame.")

        logger.debug('[proc {}] RTVideoClient acquired frame id {} pos {} of size: {}. get frame {} ms'.format(
            os.getpid(), self._fid - 1, self.current_fid, img.shape, int(1000*(time.time()-tic))))
        return img


class RTImageSequenceClient(RTVideoClient):
    def __init__(self, app, video_uri,
                 network_connector=None, video_params=None, max_wh=None,
                 loop=False, random_start=False):
        assert app in ['lego', 'pingpong', 'face',
                       'pool', 'ikea'], 'Unknown app: {}'.format(app)
        self.video_uri = video_uri
        self._cam = None
        self._start_time = None
        self._fps = 30
        self._start_fid = 0
        self._cam_frame_cnt = len(
            glob.glob(os.path.join(self.video_uri, '*.jpg')))
        assert self._cam_frame_cnt > 0, '{} has no frames. Is your video_uri correct?'.format(
            video_uri)
        if random_start:
            self._start_fid = random.randint(0, self._cam_frame_cnt - 1)
        self._fid = self._start_fid
        self._max_wh = max_wh
        self._loop = loop
        self._app = app
        self._nc = network_connector
        if video_params is not None:
            self._set_cam_params(video_params)
        assert self._fid is not None, 'Camera position needs to be initialized using _set_cam_pos'
        logger.info('[pid {}] initialized a video client. video_uri: {}, video_params: {}, loop: {},\
                    start_fid: {}, total frame_cnt: {}, fps: {}'.format(
            os.getpid(),
            video_uri,
            video_params,
            self._loop,
            self._start_fid,
            self._cam_frame_cnt,
            self._fps
        ))

    def _get_frame_bytes(self, frame_index=None):
        """frame_index is the frame idx one wants to get.
        frame_index starts with 0 for the 1st frame.
        """
        if frame_index is None:
            frame_index = self._fid
        if self._loop:
            frame_index = frame_index % self._cam_frame_cnt

        # on-disk jpeg sequence starts with 1 while our frame index starts with 0
        jpeg_fp = os.path.join(
            self.video_uri, '{:010d}.jpg'.format(frame_index + 1))
        frame_bytes = None
        with open(jpeg_fp, 'r') as f:
            frame_bytes = f.read()
        self._fid = frame_index + 1
        return True, frame_bytes

    def get_and_send_frame(self, filter_func=None, reply=False, **kwargs):
        """Public convenient function to get and send a frame."""
        frame_bytes = self.get_frame()
        ts = time.time()
        if filter_func is None or filter_func(frame_bytes):
            self.send_frame(frame_bytes, self._fid - 1,
                            reply=reply, time=ts, **kwargs)

    def get_frame(self):
        """Public function to get a frame.
        """
        tic = time.time()
        if self._fid == self._start_fid:
            has_frame, img = self._get_frame_bytes()
            self._start_time = time.time()
            if not has_frame or img is None:
                raise ValueError("Failed to get another frame.")
        else:
            # _fid starts with 0 and represents next available frame
            next_fid = self._fps * \
                (time.time() - self._start_time) + self._start_fid
            next_fid = int(next_fid)

            # the get_frame is request too soon.
            # current frame has already sampled. need to block and sleep
            if next_fid < self._fid:
                sleep_time = self._start_time + (self._fid - self._start_fid) * \
                    (1. / self._fps) - time.time()
                logger.debug("Going to sleep {} for frame {}".format(
                    sleep_time, self._fid))
                time.sleep(sleep_time)
                next_fid = self._fid

            # fast-forward
            has_frame, img = self._get_frame_bytes(frame_index=next_fid)
            if not has_frame or img is None:
                raise ValueError("Failed to get another frame.")

        logger.info('[proc {}] RTImageSequenceClient acquired frame id {} pos {}. get frame {} ms'.format(
            os.getpid(), self._fid - 1, self.current_fid, int(1000*(time.time()-tic))))
        return img


if __name__ == "__main__":
    video_uri = '/home/junjuew/work/resource-management/data/lego-trace/1/video-images'
    vc = RTImageSequenceClient('lego', video_uri, None)
    idx = 0
    while True:
        idx += 1
        img = vc.get_frame()
        logger.debug(
            "Original frame id {}, obtained frame count {}".format(vc._fid, idx))
        assert img is not None
