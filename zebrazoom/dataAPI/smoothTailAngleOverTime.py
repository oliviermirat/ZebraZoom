import zebrazoom.dataAPI as dataAPI
import numpy as np
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d

def resample_curve(points, num_points):
  deltas = np.diff(points, axis=0)
  dists = np.sqrt((deltas**2).sum(axis=1))
  cumulative = np.insert(np.cumsum(dists), 0, 0)

  if cumulative[-1] == 0:
    # All points are the same, just duplicate
    return np.tile(points[0], (num_points, 1))

  fx = interp1d(cumulative, points[:, 0], kind='linear')
  fy = interp1d(cumulative, points[:, 1], kind='linear')

  equal_spacing = np.linspace(0, cumulative[-1], num_points)
  x_new = fx(equal_spacing)
  y_new = fy(equal_spacing)
  return np.stack([x_new, y_new], axis=1)

def smooth_and_resample(dataHead, dataTailX, dataTailY, dontSmoothTail, window_length=9, polyorder=2):
  # Smooth head
  head_x = savgol_filter(dataHead[:, 0], window_length, polyorder)
  head_y = savgol_filter(dataHead[:, 1], window_length, polyorder)
  dataHeadSmoothed = np.stack([head_x, head_y], axis=1)

  # Smooth tail
  if dontSmoothTail:
    tail_x_smooth = dataTailX
    tail_y_smooth = dataTailY
  else:
    tail_x_smooth = savgol_filter(dataTailX, window_length, polyorder, axis=0)
    tail_y_smooth = savgol_filter(dataTailY, window_length, polyorder, axis=0)

  # Resample tail to ensure equal spacing (per frame)
  N, T = tail_x_smooth.shape
  resampled_tail_x = np.zeros((N, T))
  resampled_tail_y = np.zeros((N, T))

  for i in range(N):
    tail_curve = np.stack([tail_x_smooth[i], tail_y_smooth[i]], axis=1)
    resampled = resample_curve(tail_curve, T)
    resampled_tail_x[i] = resampled[:, 0]
    resampled_tail_y[i] = resampled[:, 1]

  return dataHeadSmoothed, resampled_tail_x, resampled_tail_y


def smoothTailAngleOverTime(videoName: str, nbWells: int, nbAnimalsPerWell: int, freqAlgoPosFollow: int, startTimeInSeconds = None, endTimeInSeconds = None, dontSmoothTail=0):
  
  for numWell in range(nbWells):
    
    for numAnimal in range(nbAnimalsPerWell):
      dataHead = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "HeadPos")
      dataTailX = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "TailPosX")
      dataTailY = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "TailPosY")
      
      dataHead, dataTailX, dataTailY = smooth_and_resample(dataHead, dataTailX, dataTailY, dontSmoothTail)
      
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "HeadPos", dataHead)
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "TailPosX", dataTailX)
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "TailPosY", dataTailY)
