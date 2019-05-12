from __future__ import print_function

import os
import cv2
from openvino.inference_engine import IENetwork, IEPlugin

MIN_SCORE_THRESH = 0.5
MODEL_XML = 'ssd_frozen_inference_graph.xml'
MODEL_BIN = 'ssd_frozen_inference_graph.bin'
DEVICE = 'CPU'
CATEGORY_INDEX = {1: {'id': 1, 'name': 'shadetop'}, 2: {'id': 2, 'name': 'bulbtop'}, 3: {'id': 3, 'name': 'buckle'}, 4: {'id': 4, 'name': 'lamp'}, 5: {'id': 5, 'name': 'pipe'}, 6: {'id': 6, 'name': 'blackcircle'}, 7: {'id': 7, 'name': 'base'}, 8: {'id': 8, 'name': 'shade'}, 9: {'id': 9, 'name': 'bulb'}}


class IkeaHandler(object):
    def __init__(self):
        net = IENetwork(model=MODEL_XML, weights=MODEL_BIN)
        self.input_blob = next(iter(net.inputs))
        self.out_blob = next(iter(net.outputs))
        self.n, self.c, self.h, self.w = net.inputs[self.input_blob].shape

        self.plugin = IEPlugin(device=DEVICE, plugin_dirs=None)
        self.plugin.add_cpu_extension("libcpu_extension_sse4.so")
        self.exec_net = self.plugin.load(network=net)

    def process(self, img):

        # from object_detection_demo_ssd_async.py
        img = cv2.resize(img, (self.w, self.h))
        img = img.transpose((2, 0, 1))  # Change data layout from HWC to CHW
        img = img.reshape((self.n, self.c, self.h, self.w))

        res = self.exec_net.infer(inputs={self.input_blob: img})

        detections_to_print = []
        for obj in res['DetectionOutput'][0][0]:
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
