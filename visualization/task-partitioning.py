
# %%
from __future__ import absolute_import, division, print_function

import ast
import numpy as np

from rmexp import dbutils, config
from rmexp.schema import models
from logzero import logger


# %%
# get the average processing time and
# data size for different partition
exps = ['lego-cloudlet002-2core', 'lego-nexus6']
names = ['lego-tr{}'.format(idx) for idx in range(1, 6)]
sample_frame_ds = 691341
for exp in exps:
    for name in names:
        logger.info('==============={} {}==============='.format(exp, name))
        sess = dbutils.get_session()
        data = [[ast.literal_eval(item.speed), ast.literal_eval(item.data_length)]
                for item in sess.query(models.AppProfile.speed,
                                       models.AppProfile.data_length).filter(
                    models.AppProfile.name == name).filter(
                    models.AppProfile.exp == exp).all()]
        sess.close()
        pt, ds = list(zip(*data))
        pt = np.array(pt)
        sample_pt = np.zeros((pt.shape[0], 1))
        pt = np.concatenate([sample_pt, pt], axis=1)
        if 'cloudlet' in exp:
            # cloudlet
            pcts = np.cumsum(pt[:, ::-1], axis=1)[:, ::-1]
        else:
            # client
            pcts = np.cumsum(pt, axis=1)
        logger.info('mean: {}, std: {}'.format(
            np.average(pcts, axis=0), np.std(pcts, axis=0)))

        ds = np.array(ds)
        sample_ds = np.full((ds.shape[0], 1),
                            sample_frame_ds, dtype=np.int64)
        ds = np.concatenate([sample_ds, ds], axis=1)


# %%
