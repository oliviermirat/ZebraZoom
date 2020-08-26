import numpy as np
from scipy.interpolate import UnivariateSpline

#Heading change in degrees
def getTailLength(curbout):
  return np.sum(np.abs(np.diff(curbout["TailAngle_smoothed"])))