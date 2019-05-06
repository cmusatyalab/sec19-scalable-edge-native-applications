from __future__ import absolute_import, division, print_function

try:
    import cPickle as pickle
except:
    import pickle

def serialize_list(*args):
    return pickle.dumps(args, protocol=pickle.HIGHEST_PROTOCOL)
