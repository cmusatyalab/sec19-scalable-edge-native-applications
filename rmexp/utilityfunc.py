import numpy as np

def create_latency_sigmoid(lo_x, hi_x, lo_y=0.9, hi_y=0.1):
    # y = 1 / (1 + exp^(ax-b))
    # => xa - b = ln(1/y - 1)
    a , b = np.linalg.solve([[lo_x, -1], [hi_x, -1]], np.log([1./lo_y - 1, 1./hi_y - 1]))
    return lambda x: 1. / (1. + np.exp(a*x - b))

# Based on Zhuo's SEC'17
app_default_utility_func = {
    'lego': create_latency_sigmoid(600, 2700),
    'pingpong': create_latency_sigmoid(150, 230),
    'pool': create_latency_sigmoid(95, 105),
    'face': create_latency_sigmoid(370, 1000),
}