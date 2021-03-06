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

from __future__ import print_function

import os
import time

import cv2
import numpy as np
import pkg_resources
from PIL import Image

import tensorflow as tf
from object_detection.utils import label_map_util
from ikea import fsm

MODEL_DIR = 'tf_model'
FROZEN_INFERENCE_GRAPH = pkg_resources.resource_filename(__name__,
                                                         os.path.join(
                                                             MODEL_DIR, 'ssd_frozen_inference_graph.pb'))
LABEL_MAP = pkg_resources.resource_filename(
    __name__,
    os.path.join(MODEL_DIR, 'ikea_label_map.pbtxt'))
MIN_SCORE_THRESH = 0.5


def create_detection_graph():
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(FROZEN_INFERENCE_GRAPH, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')
    return detection_graph


def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)


class IkeaHandler(object):
    def __init__(self, tfconfig=None, im_h=200, im_w=300):
        self._fsm = fsm.IkeaFSM(im_h=im_h, im_w=im_w)
        self.category_index = label_map_util.create_category_index_from_labelmap(
            LABEL_MAP, use_display_name=True)
        self.detection_graph = create_detection_graph()
        self.tensor_dict = self._construct_tensor_dict()
        self.sess = tf.Session(graph=self.detection_graph, config=tfconfig)
        self.image_tensor = self.detection_graph.get_tensor_by_name(
            'image_tensor:0')

    def _construct_tensor_dict(self):
        # Get handles to input and output tensors
        ops = self.detection_graph.get_operations()
        all_tensor_names = {output.name for op in ops for output in op.outputs}
        tensor_dict = {}
        for key in [
                'num_detections', 'detection_boxes', 'detection_scores',
                'detection_classes'
        ]:
            tensor_name = key + ':0'
            if tensor_name in all_tensor_names:
                tensor_dict[key] = self.detection_graph.get_tensor_by_name(
                    tensor_name)

        return tensor_dict

    def process(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(img)
        image_np = load_image_into_numpy_array(image)

        output_dict = self.sess.run(
            self.tensor_dict, feed_dict={self.image_tensor: np.expand_dims(image_np, 0)})

        detection_classes = output_dict['detection_classes'][0].astype(
            np.uint8)
        detection_boxes = output_dict['detection_boxes'][0]
        detection_scores = output_dict['detection_scores'][0]

        detections_to_print = []
        for detection_class, box, score in zip(
                detection_classes, detection_boxes, detection_scores):
            if score > MIN_SCORE_THRESH:
                detections_to_print.append(
                    '{} {}'.format(
                        self.category_index[detection_class]['name'], box))

        if len(detections_to_print) == 0:
            return 'No objects detected'
        else:
            concatenated_detections = ', '.join(detections_to_print)
            return 'Detected Objects: {}'.format(concatenated_detections)

    def add_symbolic_state_for_instruction(self, symbolic_state):
        """Get current instruction from symbolic states.
        This is a stateful action, the order of symbolic_state passed
        has an effect on instruction produced.

        symbolic_state: the results returned from process function above.
        """
        return self._fsm.add_symbolic_state_for_instruction(symbolic_state)


def main():
    handler = IkeaHandler()
    cap = cv2.VideoCapture('ikea.mp4')
    ret, frame = cap.read()
    with open('times.txt', 'w') as f:
        while (cap.isOpened() and ret == True):
            print(handler.process(frame, f))
            ret, frame = cap.read()


if __name__ == '__main__':
    main()
