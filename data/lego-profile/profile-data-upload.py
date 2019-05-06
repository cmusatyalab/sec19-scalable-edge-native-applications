from __future__ import absolute_import, division, print_function

import numpy as np
import sqlalchemy as sql

from rmexp import dbutils, config
from rmexp.schema import models
from logzero import logger
import operator
import itertools

def main():
    sess = dbutils.get_session()
    sess.close()

if __name__ == "__main__":
    main()