# initializes python path so that imports can be resolved
# this is due to the lego code is not written in a path
# agnostic way
import sys
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)
