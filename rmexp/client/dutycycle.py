from __future__ import absolute_import, division, print_function

import os
from scipy.stats import norm


def lego_dynamic_sampling_rate(x):
    """Returns the dyanmic sampling rate for LEGO. 
    x is the number of seconds after an instruction has delivered
    """
    mu, sigma = 14.98, 4.25589438744
    sr_min = 0.891662951404
    sr_max = 30.0
    recover_factor = 2
    return sr_min + float(sr_max - sr_min) * min(recover_factor * norm.cdf(
        x, mu, sigma), 1.0)


def ikea_dynamic_sampling_rate(x):
    """Returns the dyanmic sampling rate for ikea. 
    x is the number of seconds after an instruction has delivered
    mu is average stage legnth
    sigma is std of stage length
    """
    mu, sigma = 25.30, 12.88
    sr_min = 1.0
    sr_max = 30.0
    recover_factor = 2
    return sr_min + float(sr_max - sr_min) * min(recover_factor * norm.cdf(
        x, mu, sigma), 1.0)


if __name__ == "__main__":
    pass
