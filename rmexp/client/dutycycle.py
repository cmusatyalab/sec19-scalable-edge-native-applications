from __future__ import absolute_import, division, print_function

import os
from scipy.stats import norm


mu, sigma = 14.98, 4.25589438744
sr_min = 0.891662951404
sr_max = 30.0
recover_factor = 2


def lego_dynamic_sampling_rate(x):
    """Returns the dyanmic sampling rate for LEGO. 
    x is the number of seconds after an instruction has delivered
    """
    return sr_min + float(sr_max - sr_min) * min(recover_factor * norm.cdf(
        x, mu, sigma), 1.0)


if __name__ == "__main__":
    pass
