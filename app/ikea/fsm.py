import ast
import re
import collections
import numpy as np


class IkeaFSM(object):
    """A Lego FSM based on cumulative model."""

    def __init__(self, im_h, im_w):
        self._states = ["start", "nothing", "base", "pipe", "shade", "buckle",
                        "blackcircle", "shadebase", "bulb", "bulbtop"]
        self.current_state = "nothing"
        self._objects = ["base", "pipe", "shade", "shadetop",
                         "buckle", "blackcircle", "lamp", "bulb", "bulbtop"]
        self._staging_cnt = collections.defaultdict(int)
        self._im_h = im_h
        self._im_w = im_w
        self.one_buckle_frame_counter = 0
        self.two_buckle_frame_counter = 0

    def change_state_for_instruction(self, gabriel_msg):
        gabriel_msg.data = gabriel_msg.data + \
            '|| {} !!State Change!!'.format(self.current_state)

    def add_symbolic_state_for_instruction(self,
                                           symbolic_state):
        if self.process_ss(symbolic_state):
            return '|| {} !!State Change!!'.format(self.current_state)
        else:
            return None

    def _get_objects(self, ss):
        objs = []
        # tf's output format ymin, xmin, ymax, xmax
        # zhuo's objects format: [x1, y1, x2, y2, confidence, cls_idx]
        if 'Detected Objects: ' in ss:
            obj_dets = ss.replace('Detected Objects: ', '').split(', ')
            for obj_det in obj_dets:
                obj_name = obj_det.split(' ')[0]
                loc_str = obj_det.replace(obj_name, '')
                # try to match floating point number first
                # and then match both scientification notaion
                loc_matches = re.findall(
                    r'(\d+\.*\d*)', loc_str)
                loc = map(float, loc_matches)
                if len(loc) != 4:
                    loc_matches = re.findall(
                        r'(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)', loc_str)
                    loc = map(float, loc_matches)
                assert len(loc) == 4, loc_str
                assert obj_name in self._objects
                objs.append([loc[1] * self._im_w,
                             loc[0] * self._im_h,
                             loc[3] * self._im_w,
                             loc[2] * self._im_h,
                             1.0, self._objects.index(obj_name)])
        return np.array(objs)

    def process_ss(self, ss):
        objects = self._get_objects(ss)
        if len(objects.shape) < 2:
            return False

        object_counts = []
        for i in xrange(len(self._objects)):
            object_counts.append(sum(objects[:, -1] == i))

        prev_state = self.current_state
        if self.current_state == "nothing":
            if object_counts[0] > 0 and object_counts[1] > 0:
                if self._check_pipe(objects):
                    self.current_state = "pipe"
            elif object_counts[0] > 0:
                self.current_state = "base"
        elif self.current_state == "base":
            if object_counts[0] > 0 and object_counts[1] > 0:
                if self._check_pipe(objects):
                    self.current_state = "pipe"
        elif self.current_state == "pipe":
            if object_counts[2] > 0:
                self.current_state = "shade"
        elif self.current_state == "shade":
            if object_counts[3] > 0 and object_counts[4] > 0:
                n_buckles = self._check_buckle(objects)
                if n_buckles == 2:
                    self.one_buckle_frame_counter = 0
                    self.two_buckle_frame_counter += 1
                    if self.two_buckle_frame_counter > 3:
                        self.current_state = "buckle"
        elif self.current_state == "buckle":
            if object_counts[5] > 0:
                self.current_state = "blackcircle"
        elif self.current_state == "blackcircle":
            if object_counts[6] > 0:
                self.current_state = "shadebase"
        elif self.current_state == "shadebase":
            if object_counts[7] > 0:
                self.current_state = "bulb"
        elif self.current_state == "bulb":
            if object_counts[3] > 0 and object_counts[8] > 0:
                if self._check_bulbtop(objects):
                    self.current_state = "bulbtop"
        elif self.current_state == "bulbtop":
            self.current_state = "nothing"

        if prev_state != self.current_state:
            return True
        else:
            return False

    def _check_pipe(self, objects):
        bases = []
        pipes = []
        for i in xrange(objects.shape[0]):
            if int(objects[i, -1] + 0.1) == 0:
                bases.append(objects[i, :])
            if int(objects[i, -1] + 0.1) == 1:
                pipes.append(objects[i, :])

        for base in bases:
            base_center = ((base[0] + base[2]) / 2, (base[1] + base[3]) / 2)
            base_width = base[2] - base[0]
            base_height = base[3] - base[1]
            for pipe in pipes:
                pipe_center = ((pipe[0] + pipe[2]) / 2,
                               (pipe[1] + pipe[3]) / 2)
                pipe_height = pipe[3] - pipe[1]
                if pipe_center[1] > base_center[1]:
                    continue
                if pipe_center[0] < base_center[0] - base_width * 0.25 or pipe_center[0] > base_center[0] + base_width * 0.25:
                    continue
                if pipe_height / base_height < 1.5:
                    continue
                return True
        return False

    def _check_buckle(self, objects):
        shadetops = []
        buckles = []
        for i in xrange(objects.shape[0]):
            if int(objects[i, -1] + 0.1) == 3:
                shadetops.append(objects[i, :])
            if int(objects[i, -1] + 0.1) == 4:
                buckles.append(objects[i, :])

        for shadetop in shadetops:
            shadetop_center = (
                (shadetop[0] + shadetop[2]) / 2, (shadetop[1] + shadetop[3]) / 2)
            shadetop_width = shadetop[2] - shadetop[0]
            shadetop_height = shadetop[3] - shadetop[1]

            left_buckle = False
            right_buckle = False
            for buckle in buckles:
                buckle_center = (
                    (buckle[0] + buckle[2]) / 2, (buckle[1] + buckle[3]) / 2)
                if buckle_center[1] < shadetop[1] or buckle_center[1] > shadetop[3]:
                    continue
                if buckle_center[0] < shadetop[0] or buckle_center[0] > shadetop[2]:
                    continue
                if buckle_center[0] < shadetop_center[0]:
                    left_buckle = True
                else:
                    right_buckle = True
            if left_buckle and right_buckle:
                break

        return int(left_buckle) + int(right_buckle)

    def _check_bulbtop(self, objects):
        shadetops = []
        bulbtops = []
        for i in xrange(objects.shape[0]):
            if int(objects[i, -1] + 0.1) == 3:
                shadetops.append(objects[i, :])
            if int(objects[i, -1] + 0.1) == 8:
                bulbtops.append(objects[i, :])

        for shadetop in shadetops:
            shadetop_center = (
                (shadetop[0] + shadetop[2]) / 2, (shadetop[1] + shadetop[3]) / 2)
            shadetop_width = shadetop[2] - shadetop[0]
            shadetop_height = shadetop[3] - shadetop[1]

            for bulbtop in bulbtops:
                bulbtop_center = (
                    (bulbtop[0] + bulbtop[2]) / 2, (bulbtop[1] + bulbtop[3]) / 2)
                if bulbtop_center[1] < shadetop[1] or bulbtop_center[1] > shadetop[3]:
                    continue
                if bulbtop_center[0] < shadetop[0] or bulbtop_center[0] > shadetop[2]:
                    continue
                if bulbtop_center[0] < shadetop_center[0] - shadetop_width * 0.25 or bulbtop_center[0] > shadetop_center[0] + shadetop_width * 0.25:
                    continue
                if bulbtop_center[1] < shadetop_center[1] - shadetop_height * 0.25 or bulbtop_center[1] > shadetop_center[1] + shadetop_height * 0.25:
                    continue
                return True
        return False
