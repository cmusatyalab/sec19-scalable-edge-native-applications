
# %%
from __future__ import absolute_import, division, print_function

import ast
import numpy as np

from rmexp import dbutils, config
from rmexp.schema import models
from logzero import logger
import matplotlib.pyplot as plt

# %%
# get the average processing time and
# data size for different partition
exp_cloudlet = 'lego-cloudlet002-2core'
exp_mobile = 'lego-nexus6'
exps = [exp_cloudlet, exp_mobile]
names = ['lego-tr{}'.format(idx) for idx in range(1, 6)]
sample_frame_ds = 691341

# %%


def get_data(exp, trace):
    """Get data for experimen exp and trace.
    Return cumulative processing time and datasize as 2D numpy array (frame_id, partiion)
    """
    logger.info('processing {} {}'.format(exp, trace))
    sess = dbutils.get_session()
    data = [[ast.literal_eval(item.speed), ast.literal_eval(item.data_length)]
            for item in sess.query(models.AppProfile.speed,
                                   models.AppProfile.data_length).filter(
                models.AppProfile.name == trace).filter(
                models.AppProfile.exp == exp).all()]
    sess.close()
    pt, ds = list(zip(*data))
    pt = np.array(pt)
    sample_pt = np.zeros((pt.shape[0], 1))
    pt = np.concatenate([sample_pt, pt], axis=1)
    if 'cloudlet' in exp:
        # cloudlet
        pct = np.cumsum(pt[:, ::-1], axis=1)[:, ::-1]
    else:
        # client
        pct = np.cumsum(pt, axis=1)

    ds = np.array(ds)
    sample_ds = np.full((ds.shape[0], 1),
                        sample_frame_ds, dtype=np.int64)
    ds = np.concatenate([sample_ds, ds], axis=1)
    return pct, ds


# %%
# summarize over all traces
data = {}
for exp in exps:
    pcts, dss = [], []
    for name in names:
        pct, ds = get_data(exp, name)
        pcts.append(pct)
        dss.append(ds)
    pcts, dss = np.concatenate(pcts), np.concatenate(dss)
    data[exp] = (pcts, dss)
# %%
%matplotlib notebook

plt.boxplot(data[exp_cloudlet][0])
