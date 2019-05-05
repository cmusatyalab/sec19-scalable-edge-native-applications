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
import openface
from openface.alignment import NaiveDlib
import os
import pickle
import sys
import time

sys.path.insert(0, "..")
import config
import zhuocv as zc

current_milli_time = lambda: int(round(time.time() * 1000))

openface_root = os.getenv('OPEN_FACE_ROOT', '.')
modelDir = os.path.join(openface_root, 'models')
dlibModelDir = os.path.join(modelDir, 'dlib')
openfaceModelDir = os.path.join(modelDir, 'openface')

align = NaiveDlib(os.path.join(dlibModelDir, "mean.csv"), os.path.join(dlibModelDir, "shape_predictor_68_face_landmarks.dat"))
net = openface.TorchWrap(os.path.join(openfaceModelDir, 'nn4.v1.t7'), imgDim=96, cuda=False)
svmModelPath = os.path.join(openfaceModelDir, "celeb-classifier.nn4.v1.pkl")

#############################################################
def set_config(is_streaming):
    config.setup(is_streaming)

def process(img, display_list):
    ## the face feature (of the largest face)
    rep = zc.get_face_feature(img, align = align, align_img_dim = 96, net = net)
    if rep is None:
        rtn_msg = {'status' : 'fail'}
        return (rtn_msg, None)

    with open(svmModelPath, 'r') as f:
        (le, svm) = pickle.load(f)
    predictions = svm.predict_proba(rep)[0]
    maxI = np.argmax(predictions)
    person = le.inverse_transform(maxI)
    confidence = predictions[maxI]
    print("Predict {} with {:.2f} confidence.".format(person, confidence))

    state = (person, confidence)

    rtn_msg = {'status' : 'success'}
    return (rtn_msg, state)
