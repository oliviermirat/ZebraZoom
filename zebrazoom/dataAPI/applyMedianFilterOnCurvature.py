import numpy as np
from scipy import ndimage

def applyMedianFilterOnCurvature(curvatureValues: np.array, rolling_window: int=3) -> np.array:
  
  curvatureValues = ndimage.median_filter(curvatureValues, size=rolling_window)
  
  return curvatureValues
