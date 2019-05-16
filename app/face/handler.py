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

import json
import os
import pickle
import select
import socket
import struct
import sys
import threading
import time
import traceback

import cv2
import dlib
import numpy as np
import pkg_resources
from face import config


detector = dlib.get_frontal_face_detector()
face_landmarks_data_fp = pkg_resources.resource_filename(
    __name__, "models/shape_predictor_68_face_landmarks.dat")
face_recognition_model_data_fp = pkg_resources.resource_filename(
    __name__, "models/dlib_face_recognition_resnet_model_v1.dat")
sp = dlib.shape_predictor(face_landmarks_data_fp)
facerec = dlib.face_recognition_model_v1(face_recognition_model_data_fp)
face_svm_data_fp = pkg_resources.resource_filename(
    __name__, "models/model_dlib.pkl"
)

with open(face_svm_data_fp, 'rb') as f:
    (le, svm) = pickle.load(f)


def dlib_face(img):
    sk_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    dets = detector(sk_img, 1)
    face_det = None
    max_area = 0
    for k, d in enumerate(dets):
        if d.width() * d.height() > max_area:
            max_area = d.width() * d.height()
            face_det = dets[k]

    if max_area == 0:
        return None

    # Get the landmarks/parts for the face in box d.
    shape = sp(sk_img, face_det)
    face_descriptor = facerec.compute_face_descriptor(sk_img, shape)
    return face_descriptor


class FaceHandler(object):
    def process(self, img):
        if max(img.shape) > config.IMAGE_MAX_WH:
            resize_ratio = (float(config.IMAGE_MAX_WH) /
                            max(img.shape[0], img.shape[1]))
            img = cv2.resize(img, (0, 0), fx=resize_ratio,
                             fy=resize_ratio, interpolation=cv2.INTER_AREA)

        face_rep = dlib_face(img)
        if face_rep is None:
            return "No Face"

        face_rep = np.array(face_rep)
        face_rep = face_rep.reshape(1, -1)
        predictions = svm.predict_proba(face_rep)[0]
        maxI = np.argmax(predictions)
        person = le.inverse_transform([maxI])[0]
        confidence = predictions[maxI]

        if confidence > 0.05:
            return person

        return "Unknown Face"


def main():
    handler = FaceHandler()
    cap = cv2.VideoCapture('/face_testing_data/face.mp4')
    ret, frame = cap.read()
    while (cap.isOpened() and ret == True):
        print(handler.process(frame))
        ret, frame = cap.read()


if __name__ == '__main__':
    main()
