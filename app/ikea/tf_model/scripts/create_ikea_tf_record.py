
# Copyright 2019 Carnegie Mellon University
#
# This is based on the following file:
# https://github.com/tensorflow/models/blob/master/research/object_detection/dataset_tools/create_pet_tf_record.py
# The original file is licensed under the Apache License, Version 2.0 with
# the following copyright notice:
# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import hashlib
import io
import os
import random

import contextlib2
import PIL.Image
import tensorflow as tf
import pickle
import logging

from object_detection.utils import dataset_util
from object_detection.utils import label_map_util

flags = tf.app.flags
flags.DEFINE_string('label_dir', '', 'Directory with labels')
flags.DEFINE_string('image_dir', '', 'Directory with images')
flags.DEFINE_string('label_map_path', 'ikea_label_map.pbtxt',
                    'Path to label map proto')

FLAGS = flags.FLAGS

TRAIN_FILENAME = 'train.record'
ORIGINAL_PATH = '/home/junjuew/object-detection-web/demo-web/vatic/videos/'


def filename_to_tf_example(img_path, label_path, label_map_dict):
    with tf.gfile.GFile(img_path, 'rb') as fid:
        encoded_jpg = fid.read()
        encoded_jpg_io = io.BytesIO(encoded_jpg)
        image = PIL.Image.open(encoded_jpg_io)
        if image.format != 'JPEG':
            raise ValueError('Image format not JPEG')
        key = hashlib.sha256(encoded_jpg).hexdigest()

        width, height = image.size

        xmins = []
        ymins = []
        xmaxs = []
        ymaxs = []
        classes = []
        classes_text = []

        with open(label_path) as label_file:
            for line in label_file:
                contents = line.split()
                pixel_xmin = int(contents[0])
                pixel_ymin = int(contents[1])
                pixel_width = int(contents[2])
                pixel_height = int(contents[3])
                label = contents[4]

                xmin = pixel_xmin / width
                ymin = pixel_ymin / height
                xmax = (pixel_xmin + pixel_width) / width
                ymax = (pixel_ymin + pixel_height) / height

                xmins.append(xmin)
                ymins.append(ymin)
                xmaxs.append(xmax)
                ymaxs.append(ymax)
                classes.append(label_map_dict[label])
                classes_text.append(label.encode('utf8'))

            feature_dict = {
                'image/height': dataset_util.int64_feature(height),
                'image/width': dataset_util.int64_feature(width),
                'image/key/sha256': dataset_util.bytes_feature(key.encode('utf8')),
                'image/encoded': dataset_util.bytes_feature(encoded_jpg),
                'image/format': dataset_util.bytes_feature('jpeg'.encode('utf8')),
                'image/object/bbox/xmin': dataset_util.float_list_feature(xmins),
                'image/object/bbox/xmax': dataset_util.float_list_feature(xmaxs),
                'image/object/bbox/ymin': dataset_util.float_list_feature(ymins),
                'image/object/bbox/ymax': dataset_util.float_list_feature(ymaxs),
                'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
                'image/object/class/label': dataset_util.int64_list_feature(classes),
            }

            example = tf.train.Example(features=tf.train.Features(feature=feature_dict))
            return example

    raise Exception('Error creating example')


def main(_):
    logging.basicConfig(level=logging.INFO)

    label_dir = FLAGS.label_dir
    image_dir = FLAGS.image_dir
    label_map_dict = label_map_util.get_label_map_dict(FLAGS.label_map_path)

    with contextlib2.ExitStack() as tf_record_close_stack:
        output_record = tf_record_close_stack.enter_context(
            tf.python_io.TFRecordWriter(TRAIN_FILENAME))
        with open('train.txt') as f:
            for line in f:
                line_contents = line.split()
                label_number = line_contents[0]
                original_image_path = line_contents[1]

                image_path_ending = original_image_path.replace(
                    ORIGINAL_PATH, '')
                image_path = os.path.join(image_dir, image_path_ending)

                label_path = os.path.join(
                    label_dir, '{}.txt'.format(label_number))

                tf_example = filename_to_tf_example(
                    image_path, label_path, label_map_dict)
                output_record.write(tf_example.SerializeToString())


if __name__ == '__main__':
    tf.app.run()
