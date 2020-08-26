import numpy as np
from scipy.interpolate import UnivariateSpline

#Heading change in degrees
def getTailLength2(tailangle):
  return np.sum(np.abs(np.diff(tailangle)))