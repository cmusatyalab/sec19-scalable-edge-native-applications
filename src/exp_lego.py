#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

import cv2
import fire

from lego import lego


def main(video_uri):
    lego_app = lego.LegoHandler()
    cam = cv2.VideoCapture(video_uri)
    has_frame = True
    while has_frame:
        has_frame, img = cam.read()
        if img is not None:
            result = lego_app.handle_img(img)
            print(result)


if __name__ == "__main__":
    fire.Fire(main)
