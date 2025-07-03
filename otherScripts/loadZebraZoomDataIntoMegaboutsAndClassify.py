###
### This script requires installing Megabouts: https://megabouts.ai/usage.html#installing-megabouts
###


# Specify the ZebraZoom output you want to use, well and animal number to consider, and recording conditions

path_to_h5_file = "set_the_path_to_your_h5_file_here"

nbWell = 0
nbAnimal = 0

fps          = 30
mm_per_unit  = 0.1

showFullEthogram = True
showBoutsSegmentation = False

startSecond = 0 # used for ethogram and bout segmentation plots
endSecond   = 5 # used for ethogram and bout segmentation plots

showBoutClassifiedWithMinimumThreshold = False
probThreshold = 0.5


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
from megabouts.pipeline import FullTrackingPipeline
from cycler import cycler
import matplotlib.gridspec as gridspec
from megabouts.utils import (
    bouts_category_name,
    bouts_category_name_short,
    bouts_category_color,
    cmp_bouts,
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


# Running Megabouts full pipeline

pipeline = FullTrackingPipeline(tracking_cfg, exclude_CS=True)

pipeline.segmentation_cfg.threshold = 50

pipeline.tail_preprocessing_cfg

pipeline.tail_preprocessing_cfg.savgol_window

ethogram, bouts, segments, tail, traj = pipeline.run(tracking_data)


# Bout segmentation visualization

if showBoutsSegmentation:

  fig, ax = plt.subplots(2, 1, figsize=(15, 5), sharex=True)

  x = tracking_data._tail_angle[:, 7]
  ax[0].plot(x)
  ax[0].plot(segments.onset, x[segments.onset], "x", color="green")
  ax[0].plot(segments.offset, x[segments.offset], "x", color="red")
  ax[0].plot(segments.HB1, x[segments.HB1], "x", color="blue")
  ax[0].set_ylim(-4, 4)

  x = tail.vigor
  ax[1].plot(x)
  ax[1].plot(segments.onset, x[segments.onset], "x", color="green")
  ax[1].plot(segments.offset, x[segments.offset], "x", color="red")

  t = np.arange(tracking_data.T) / tracking_cfg.fps
  IdSt     = startSecond * tracking_cfg.fps
  Duration = endSecond   * tracking_cfg.fps
  ax[1].set_xlim(IdSt, IdSt + Duration)

  fig, ax = plt.subplots(1, 1, figsize=(10, 3))
  x = tail.df.angle_smooth.iloc[:, 7]
  ax.plot(t, x, color="tab:grey", lw=1)
  ax.plot(t[segments.onset], x[segments.onset], "x", color="tab:green", label="onset")
  ax.plot(t[segments.offset], x[segments.offset], "x", color="tab:red", label="offset")
  ax.plot(
      t[segments.HB1], x[segments.HB1], "x", color="tab:blue", label="first tail beat"
  )
  ax.set(
      **{
          "title": "segmentation",
          "xlim": (t[IdSt], t[IdSt + Duration]),
          "ylim": (-4, 4),
          "ylabel": "tail angle (rad)",
          "xlabel": "time (s)",
      }
  )
  ax.legend()
  plt.show()


# Display bouts classified with a probability greater than probThreshold

if showBoutClassifiedWithMinimumThreshold:

  id_b = np.unique(bouts.df.label.category[bouts.df.label.proba > probThreshold]).astype("int")

  fig, ax = plt.subplots(facecolor="white", figsize=(25, 4))

  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  ax.spines["bottom"].set_visible(False)
  ax.spines["left"].set_visible(False)
  ax.set_xticks([])
  ax.set_yticks([])
  G = gridspec.GridSpec(1, len(id_b))
  ax0 = {}
  for i, b in enumerate(id_b):
      ax0 = plt.subplot(G[i])
      ax0.set_title(bouts_category_name_short[b], fontsize=15)
      for i_sg, sg in enumerate([1, -1]):
          id = bouts.df[
              (bouts.df.label.category == b)
              & (bouts.df.label.sign == sg)
              & (bouts.df.label.proba > 0.5)
          ].index
          if len(id) > 0:
              ax0.plot(sg * bouts.tail[id, 7, :].T, color="k", alpha=0.3)
          ax0.set_xlim(0, pipeline.segmentation_cfg.bout_duration)
          ax0.set_ylim(-4, 4)
          ax0.set_xticks([])
          ax0.set_yticks([])
          for sp in ["top", "bottom", "left", "right"]:
              ax0.spines[sp].set_color(bouts_category_color[b])
              ax0.spines[sp].set_linewidth(5)

  plt.show()


# Display Ethogram

if showFullEthogram:

  IdSt = startSecond * tracking_cfg.fps
  T = endSecond
  Duration = T * tracking_cfg.fps
  IdEd = IdSt + Duration
  t = np.arange(Duration) / tracking_cfg.fps

  fig = plt.figure(facecolor="white", figsize=(15, 5), constrained_layout=True)
  G = gridspec.GridSpec(2, 1, height_ratios=[1, 0.2], hspace=0.5, figure=fig)
  ax = plt.subplot(G[0, 0])
  blue_cycler = cycler(color=plt.cm.Blues(np.linspace(0.2, 0.9, 10)))
  ax.set_prop_cycle(blue_cycler)

  ax.plot(t, ethogram.df["tail_angle"].values[IdSt:IdEd, :7], lw=1)
  ax.set_ylim(-4, 4)
  ax.set_xlim(0, T)

  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  ax.spines["bottom"].set_visible(False)
  ax.get_yaxis().tick_left()
  ax.get_xaxis().set_ticks([])
  ax.set_ylabel("tail angle (rad)", rotation=0, labelpad=100)

  ax = plt.subplot(G[1, 0])
  ax.imshow(
      ethogram.df[("bout", "cat")].values[IdSt:IdEd].T,
      cmap=cmp_bouts,
      aspect="auto",
      vmin=0,
      vmax=12,
      interpolation="nearest",
      extent=(0, T, 0, 1),
  )
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  ax.spines["bottom"].set_visible(False)
  ax.get_yaxis().tick_left()
  ax.get_xaxis().set_ticks([])
  ax.get_yaxis().set_ticks([])
  ax.set_xlim(0, T)
  ax.set_ylim(0, 1.1)

  id_b = np.unique(ethogram.df[("bout", "id")].values[IdSt:IdEd]).astype("int")
  id_b = id_b[id_b > -1]
  for i in id_b:
      on_ = bouts.df.iloc[i][("location", "onset")]
      b = bouts.df.iloc[i][("label", "category")]
      ax.text((on_ - IdSt) / tracking_cfg.fps, 1.1, bouts_category_name[int(b)])

  ax.set_ylabel("bout category", rotation=0, labelpad=100)
  plt.show()
