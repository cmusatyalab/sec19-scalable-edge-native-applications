"""Application Utility Function

Utility function (F: latency --> Utility) is determined
by intrinsic application latency requirements.
"""
import scipy
import numpy as np


def create_latency_sigmoid(lo_x, hi_x, lo_y=0.9, hi_y=0.99):
    # y = 1 / (1 + exp^(ax-b))
    # => xa - b = ln(1/y - 1)
    a, b = np.linalg.solve([[lo_x, -1], [hi_x, -1]],
                           np.log([1. / lo_y - 1, 1. / hi_y - 1]))
    return lambda x: 1. / (1. + np.exp(a * x - b))


def get_slow_exponential(slow_decay_st, expo_decay_st, half_life):
    slow_decay_st, expo_decay_st, half_life = map(float,
                                                  [slow_decay_st, expo_decay_st, half_life])
    exponential_lambda = np.log(2.) / half_life
    # 1 - (x/a)^n
    slow_n = 4.0
    slow_a = (expo_decay_st - slow_decay_st) / np.power(1 - 0.9, 1 / slow_n)

    def util_one(x):
        if x <= slow_decay_st:
            return 1.0
        elif x > slow_decay_st and x <= expo_decay_st:
            return 1 - np.power((x - slow_decay_st) / slow_a, 4)
        else:
            # exponential decay
            return 0.9 * np.exp(-exponential_lambda * (x - expo_decay_st))
    return util_one


lego_util = get_slow_exponential(600, 2700, (2700 - 600) / 4.0)

# threshold based on Zhuo's SEC'17 paper
func_dict = {
    'lego': get_slow_exponential(600, 2700, (2700 - 600) / 4.0),
    # decay twice faster
    'pingpong': get_slow_exponential(150, 230, (230 - 150) / 8.0),
    'pool': get_slow_exponential(95, 105, (105 - 95) / 4.0),
    'face': get_slow_exponential(370, 1000, (1000 - 370) / 4.0),
    'ikea': get_slow_exponential(600, 2700, (2700 - 600) / 4.0),
}
