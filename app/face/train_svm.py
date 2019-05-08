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
# This script is used for testing computer vision algorithms in the
# Lego Task Assistance project. It does processing for one image.
# Usage: python img.py <image-path>
#

'''
This script loads a single image from file, and try to generate relevant information of Face Assistant.
It is primarily used as a quick test tool for the computer vision algorithm.
'''

import argparse
import cv2
import dlib
import numpy as np
import pickle
import sys
import time
import os
from sklearn import preprocessing
from sklearn.svm import SVC

from face import config
from face import zhuocv as zc

LABELS = {
    '/face_training_data/junjue1': 'Junjue',
    '/face_training_data/junjue2': 'Junjue',
    '/face_training_data/junjue3': 'Junjue',
    '/face_training_data/junjue4': 'Junjue',
    '/face_training_data/edmund1': 'Edmund',
    '/face_training_data/edmund2': 'Edmund',
    '/face_training_data/edmund3': 'Edmund',
    '/face_training_data/edmund4': 'Edmund',
    '/face_training_data/jan1': 'Jan',
    '/face_training_data/jan2': 'Jan',
    '/face_training_data/jan3': 'Jan',
    '/face_training_data/jan4': 'Jan',
    '/face_training_data/tom1': 'Tom',
    '/face_training_data/tom2': 'Tom',
    '/face_training_data/tom3': 'Tom',
    '/face_training_data/tom4': 'Tom',
    '/face_training_data/wenlu1': 'Wenlu',
    '/face_training_data/wenlu2': 'Wenlu',
    '/face_training_data/wenlu3': 'Wenlu',
    '/face_training_data/wenlu4': 'Wenlu',
    '/face_training_data/zhuo1': 'Zhuo',
    '/face_training_data/zhuo2': 'Zhuo',
    '/face_training_data/zhuo3': 'Zhuo',
    '/face_training_data/zhuo4': 'Zhuo',
}


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file",
                        help = "The image to process",
                       )
    args = parser.parse_args()
    return (args.input_file)

# set configs...
config.setup(is_streaming = False)
display_list = config.DISPLAY_LIST

detector = dlib.get_frontal_face_detector()
sp = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")
facerec = dlib.face_recognition_model_v1("models/dlib_face_recognition_resnet_model_v1.dat")

# with open("models/model_dlib.pkl", 'r') as f:
#     (le, svm) = pickle.load(f)

def dlib_face(img):
    sk_img = zc.cv_img2sk_img(img)
    dets = detector(sk_img, 1)
    face_det = None
    max_area = 0
    for k, d in enumerate(dets):
        #print("Detection {}: Left: {} Top: {} Right: {} Bottom: {}".format(
        #    k, d.left(), d.top(), d.right(), d.bottom()))

        if d.width() * d.height() > max_area:
            max_area = d.width() * d.height()
            face_det = dets[k]

    if max_area == 0:
        return None

    # Get the landmarks/parts for the face in box d.
    # print face_det
    shape = sp(sk_img, face_det)
    face_descriptor = facerec.compute_face_descriptor(sk_img, shape)
    return face_descriptor

face_reps = []
labels = []

for root, dirs, files in os.walk('/face_training_data'):
    for filename in files:
        if filename.endswith('.jpeg'):
            img = cv2.imread(os.path.join(root, filename))
            if max(img.shape) > config.IMAGE_MAX_WH:
                resize_ratio = float(config.IMAGE_MAX_WH) / max(img.shape[0], img.shape[1])
                img = cv2.resize(img, (0, 0), fx = resize_ratio, fy = resize_ratio, interpolation = cv2.INTER_AREA)

            face_rep = dlib_face(img)
            if face_rep is not None:
                face_rep = np.array(face_rep)
                face_reps.append(face_rep)
                labels.append(LABELS[root])

X = np.row_stack(face_reps)

le = preprocessing.LabelEncoder()
y = le.fit_transform(labels)
svm = SVC(probability=True)

svm.fit(X, y)

with open("models/model_dlib.pkl", 'w') as f:
    pickle.dump((le, svm), f)

# # load test image
# input_file = parse_arguments()
# img = cv2.imread(input_file)
# if max(img.shape) > config.IMAGE_MAX_WH:
#     resize_ratio = float(config.IMAGE_MAX_WH) / max(img.shape[0], img.shape[1])
#     img = cv2.resize(img, (0, 0), fx = resize_ratio, fy = resize_ratio, interpolation = cv2.INTER_AREA)

# # zc.check_and_display("input", img, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

# # process image and get the symbolic representation
# ## get current state

# for i in xrange(10):
#     face_rep = dlib_face(img)
#     if face_rep is None:
#         print "face representation is None"
#         sys.exit()

#     face_rep = np.array(face_rep)
#     face_rep = face_rep.reshape(1, -1)
#     print 'shape', face_rep.shape
#     # predictions = svm.predict_proba(face_rep)[0]
#     # maxI = np.argmax(predictions)
#     # person = le.inverse_transform(maxI)
#     # confidence = predictions[maxI]
#     # print("Predict {} with {:.2f} confidence.".format(person, confidence))

# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt as e:
#     sys.stdout.write("user exits\n")
