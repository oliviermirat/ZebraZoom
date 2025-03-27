import numpy as np
import math

def calculateHeading(coords):

  if len(coords) < 3:
      raise ValueError("At least three points are required.")

  coords = np.array(coords)

  p1, p2, p3 = coords[:3]

  v1 = p2 - p1
  v2 = p3 - p2
  
  v = (v1 + v2) / 2
  if v[0] != 0:
    angle = math.atan(v[1] / v[0])
  else:
    if v[1] > 0:
      angle = - math.pi / 2
    else:
      angle = math.pi / 2
  if v[0] > 0:
    angle = (angle + math.pi) % (2 * math.pi)

  return angle
