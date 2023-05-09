import numpy as np


class TailTrackingBase:
  @staticmethod
  def _appendPoint(x, y, points):
    curPoint = np.zeros((2, 1))
    curPoint[0] = x
    curPoint[1] = y
    points = np.append(points, curPoint, axis=1)
    return points
