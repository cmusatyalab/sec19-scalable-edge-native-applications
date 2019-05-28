import json 
import pandas as pd
import os.path as osp
import glob
import sys

def combine_traces(path_list):
    '''
    Combines video frame number with nearest sensor data 
    can ref pd df as df.loc[frame_num] = {'sensor_timestamp','rot_{x,y,z}','acc_{x,y,z}'}
    '''
    for path in path_list:
        with open(osp.join(path,'frames.json')) as f:
            df_frames = pd.DataFrame(json.load(f)['frames'])
            df_frames.set_index('time_usec', inplace=True)
        with open(osp.join(path,'rotations.json')) as f:
            df_rotations = pd.DataFrame(json.load(f)['rotations'])
            df_rotations.set_index('time_usec', inplace=True)
            df_rotations.rename(columns={'x': 'rot_x',
                                         'y': 'rot_y',
                                         'z': 'rot_z'}, inplace=True)
        with open(osp.join(path,'accelerations.json')) as f:
            df_accelerations = pd.DataFrame(json.load(f)['accelerations'])
            df_accelerations.set_index('time_usec', inplace=True)
            df_accelerations.rename(columns={'x': 'acc_x',
                                             'y': 'acc_y',
                                             'z': 'acc_z'}, inplace=True)
        df = pd.merge_asof(left=df_frames, right=df_rotations, left_index=True, 
            right_index=True, direction='nearest')
        df = pd.merge_asof(left=df, right=df_accelerations, left_index=True, 
            right_index=True, direction='nearest')
        df.set_index('frame_id', inplace=True)
        save_csv = osp.join(path,osp.basename(path)+'.csv')
        print(save_csv)
        df.to_csv(save_csv)
    #data = pd.read_csv('df.csv',index_col='frame_id')



if __name__ == "__main__":
    path_list = glob.glob(osp.join(sys.argv[1],'2019_*'))
    print(path_list)
    combine_traces(path_list)

