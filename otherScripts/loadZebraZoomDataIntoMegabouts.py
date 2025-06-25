###
### This script requires installing Megabouts: https://megabouts.ai/usage.html#installing-megabouts
###


# Specify the ZebraZoom output you want to use, well and animal number to consider, and recording conditions

path_to_h5_file = "set_the_path_to_your_h5_file_here"

nbWell = 0
nbAnimal = 0

fps          = 30
mm_per_unit  = 0.1


# Loading libraries

import numpy as np
import matplotlib.pyplot as plt
import h5py
import numpy as np

from megabouts.tracking_data import (
    TrackingConfig,
    FullTrackingData,
    HeadTrackingData,
    TailTrackingData,
    load_example_data,
)


# Extracting data from ZebraZoom output

def extract_head_tail_positions(h5_file_path, nbWell, nbAnimal):
  h5path = 'dataForWell'+str(nbWell)+'/dataForAnimal'+str(nbAnimal)
  with h5py.File(h5_file_path, 'r') as f:
    head_pos = f[h5path+'/dataPerFrame/HeadPos'][:]
    tail_pos_x = f[h5path+'/dataPerFrame/TailPosX'][:]
    tail_pos_y = f[h5path+'/dataPerFrame/TailPosY'][:]
  head_x = np.array([pos[0] for pos in head_pos])
  head_y = np.array([pos[1] for pos in head_pos])
  tail_x = np.vstack([[frame[name] for name in frame.dtype.names] for frame in tail_pos_x])
  tail_y = np.vstack([[frame[name] for name in frame.dtype.names] for frame in tail_pos_y])
  return head_x, head_y, tail_x, tail_y

head_x, head_y, tail_x, tail_y = extract_head_tail_positions(path_to_h5_file, nbWell, nbAnimal)

for i in range(1, len(head_x)):
  if head_x[i] == 0 and head_y[i] == 0:
    head_x[i] = head_x[i-1]
    head_y[i] = head_y[i-1]

for i in range(1, tail_x.shape[0]):
  if np.all(tail_x[i] == 0) and np.all(tail_y[i] == 0):
    tail_x[i] = tail_x[i-1]
    tail_y[i] = tail_y[i-1]

rows, cols = tail_x.shape
for i in range(rows):
  for j in range(cols-1):
    if tail_x[i][j] == tail_x[i][j+1] and tail_y[i][j] == tail_y[i][j+1]:
      tail_x[i][j+1] = np.nan
      tail_y[i][j+1] = np.nan


# Importing ZebraZoom extracted data into Megabouts

tracking_cfg = TrackingConfig(fps=fps, tracking="full_tracking")

head_x = head_x * mm_per_unit
head_y = head_y * mm_per_unit
tail_x = tail_x * mm_per_unit
tail_y = tail_y * mm_per_unit

tracking_data = FullTrackingData.from_keypoints(
    head_x=head_x, head_y=head_y, tail_x=tail_x, tail_y=tail_y
)



# Optional: Debugging option (if the command above is put into comment): head_x, head_y, tail_x, tail_y export

if False:
  
  import pandas as pd

  def export_to_excel(head_x, head_y, tail_x, tail_y, output_path):
    df_head = pd.DataFrame({
      'head_x': head_x,
      'head_y': head_y
    })
    df_tail_x = pd.DataFrame(tail_x, columns=[f'tail_x_{i+1}' for i in range(tail_x.shape[1])])
    df_tail_y = pd.DataFrame(tail_y, columns=[f'tail_y_{i+1}' for i in range(tail_y.shape[1])])
    df_full = pd.concat([df_head, df_tail_x, df_tail_y], axis=1)
    df_full.to_excel(output_path, index=False)

  export_to_excel(head_x, head_y, tail_x, tail_y, "head_tail_positions.xlsx")
