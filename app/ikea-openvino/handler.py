from __future__ import print_function

import os
import cv2
from openvino.inference_engine import IENetwork, IEPlugin
from enum import Enum


MIN_SCORE_THRESH = 0.5
CATEGORY_INDEX = {
    1: {'id': 1, 'name': 'shadetop'},
    2: {'id': 2, 'name': 'bulbtop'},
    3: {'id': 3, 'name': 'buckle'},
    4: {'id': 4, 'name': 'lamp'},
    5: {'id': 5, 'name': 'pipe'},
    6: {'id': 6, 'name': 'blackcircle'},
    7: {'id': 7, 'name': 'base'},
    8: {'id': 8, 'name': 'shade'},
    9: {'id': 9, 'name': 'bulb'}
}


class Detector(Enum):
    FASTER_RCNN = 1
    SSD = 2


MODEL_XML = {
    Detector.FASTER_RCNN: 'faster_rcnn_frozen_inference_graph.xml',
    Detector.SSD: 'ssd_frozen_inference_graph.xml',
}
MODEL_BIN = {
    Detector.FASTER_RCNN: 'faster_rcnn_frozen_inference_graph.bin',
    Detector.SSD: 'ssd_frozen_inference_graph.bin',
}


class IkeaHandler(object):
    def __init__(self, device='CPU', detector=Detector.SSD):
        self.detector = detector
        net = IENetwork(model=MODEL_XML[detector], weights=MODEL_BIN[detector])
        self.n, self.c, self.h, self.w = net.inputs['image_tensor'].shape

        self.plugin = IEPlugin(device=device, plugin_dirs=None)
        if device == 'CPU':
            self.plugin.add_cpu_extension("libcpu_extension_sse4.so")
        self.exec_net = self.plugin.load(network=net)

    def process(self, raw_img):

        # from object_detection_demo_ssd_async.py
        img = cv2.resize(raw_img, (self.w, self.h))
        img = img.transpose((2, 0, 1))  # Change data layout from HWC to CHW
        img = img.reshape((self.n, self.c, self.h, self.w))

        inputs = {'image_tensor': img}
        if self.detector == Detector.FASTER_RCNN:
            height, width, _ = raw_img.shape
            assert (width / height) == (self.w / self.h), (
                'Aspect ratio is wrong')            
            
            inputs['image_info'] = [self.w, self.h, 1]

        res = self.exec_net.infer(inputs=inputs)

        output_name = ('detection_output'
                       if self.detector == Detector.FASTER_RCNN
                       else 'DetectionOutput')

        detections_to_print = []
        for obj in res[output_name][0][0]:
            if obj[2] > MIN_SCORE_THRESH:
                detection_class = int(obj[1])
                box = obj[3:7]
                detections_to_print.append('{} {}'.format(
                    CATEGORY_INDEX[detection_class]['name'], box))

        if len(detections_to_print) == 0:
            return 'No objects detected'
        else:
            concatenated_detections = ', '.join(detections_to_print)
            return 'Detected Objects: {}'.format(concatenated_detections)


def main():
    handler = IkeaHandler()
    cap = cv2.VideoCapture('ikea.mp4')
    ret, frame = cap.read()
    while (cap.isOpened() and ret == True):
        print(handler.process(frame))
        ret, frame = cap.read()


if __name__ == '__main__':
    main()
