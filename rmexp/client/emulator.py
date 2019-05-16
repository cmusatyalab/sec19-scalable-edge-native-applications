from __future__ import absolute_import, division, print_function

import os
import time
import types

import cv2
import pandas as pd
from logzero import logger
from rmexp import client, schema, utils


class Sensor(object):
    def sample(self):
        pass

    def get(self, idx):
        pass


class VideoSensor(client.RTVideoClient):
    def __init__(self, trace, *args, **kwargs):
        video_uri = utils.get_trace_video_uri(trace)
        super(VideoSensor, self).__init__(video_uri, *args, **kwargs)
        logger.debug('created video sensor to read from: {}'.format(video_uri))

    def sample(self):
        frame = self.get_frame()
        return (self._fid, frame)

    def get(self, idx):
        raise NotImplementedError("VideoSensor does not allow ad-hoc query.")


class IMUSensor(Sensor):
    def __init__(self, trace):
        super(IMUSensor, self).__init__()
        self.trace = trace
        df = pd.read_sql('SELECT * FROM IMU WHERE name = %s',
                         schema.engine, params=[self.trace, ])
        df['index'] = df['index'].astype(int)
        self.df = df.sort_values('index')
        self.cur_idx = self.df['index'].iloc[0]
        logger.debug('created IMU sensor {}. Current idx: {}'.format(
            self.trace, self.cur_idx))

    def sample(self):
        self.cur_idx += 1
        return (self.cur_idx, self.get(self.cur_idx))

    def get(self, idx):
        return self.df.iloc[idx][['rot_x',
                                  'rot_y',
                                  'rot_z',
                                  'acc_x',
                                  'acc_y',
                                  'acc_z']].values


class MobileDevice(object):
    def __init__(self, sensors):
        super(MobileDevice, self).__init__()
        self.sensors = sensors

    def sample(self):
        return map(lambda x: x.sample(), self.sensors)


class CameraTimedMobileDevice(MobileDevice):
    """For each sample it get fid from Video sensor and return
    corresponding other sensor data.
    """

    def __init__(self, sensors):
        super(CameraTimedMobileDevice, self).__init__(sensors)
        assert (type(self.sensors[0]) is VideoSensor)
        self.primary_sensor = self.sensors[0]
        self.secondary_sensors = self.sensors[1:]

    def sample(self):
        (idx, pdata) = self.primary_sensor.sample()
        data = map(lambda x: x.get(idx), self.secondary_sensors)
        data = zip([idx]*len(data), data)
        data.insert(0, (idx, pdata))
        return data


if __name__ == "__main__":
    trace = 'lego-tr1'
    cam = VideoSensor(trace)
    imu = IMUSensor(trace)
    d = CameraTimedMobileDevice(
        sensors=[cam, imu]
    )
    while True:
        time.sleep(1)
        logger.info(d.sample())
