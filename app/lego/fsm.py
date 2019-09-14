"""Lego's FSM
"""


class LegoFSM(object):
    def __init__(self, cnt_to_transition=3):
        """cnt_to_transition: min cumulative/consecutive frames needed for a transition
        """
        self._state = None
        self._cnt_to_transition = cnt_to_transition
        self._staging_cnt = {}
        self._staging_ss = None

    def change_state_for_instruction(self, symbolic_state):
        self._state = symbolic_state
        self._staging_cnt.clear()
        return '!!State Change!!'

    def _process_reply_consecutive(self, symbolic_state):
        """An instruction requires consecutive detection of a video stream.
        When # of consecutive detection equals _cnt_to_transitions,
        then transition and clear counter.
        Used in sec'19 paper submission.
        """
        if '[[' in symbolic_state:
            if symbolic_state != self._staging_ss:
                self._staging_cnt.clear()

            if symbolic_state not in self._staging_cnt:
                self._staging_cnt[symbolic_state] = 0
            self._staging_cnt[symbolic_state] += 1
            self._staging_ss = symbolic_state

            if (self._staging_cnt[symbolic_state] == self._cnt_to_transition):
                if self._state != symbolic_state:
                    return self.change_state_for_instruction(symbolic_state)
        return None

    def _process_reply_cumulative(self, symbolic_state):
        """An instruction requires cumulative detection of a video stream.
        When # of detection cumulates to _cnt_to_transitions,
        then transition and clear counter.
        """
        if '[[' in symbolic_state:
            if symbolic_state not in self._staging_cnt:
                self._staging_cnt[symbolic_state] = 0
            self._staging_cnt[symbolic_state] += 1

            if (self._staging_cnt[symbolic_state]
                    >= self._cnt_to_transition):
                if self._state != symbolic_state:
                    return self.change_state_for_instruction(symbolic_state)
        return None

    def add_symbolic_state_for_instruction(self, symbolic_state):
        return self._process_reply_cumulative(symbolic_state)
