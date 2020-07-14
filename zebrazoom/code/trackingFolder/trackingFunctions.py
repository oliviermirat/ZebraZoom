import numpy as np
import math

def calculateAngle(xStart, yStart, xEnd, yEnd):
  vx = xEnd - xStart
  vy = yEnd - yStart
  if vx == 0:
    if vy > 0:
      lastFirstTheta = math.pi/2
    else:
      lastFirstTheta = (3*math.pi)/2
  else:
    lastFirstTheta = np.arctan(abs(vy/vx))
    if (vx < 0) and (vy >= 0):
      lastFirstTheta = math.pi - lastFirstTheta
    elif (vx < 0) and (vy <= 0):
      lastFirstTheta = lastFirstTheta + math.pi
    elif (vx > 0) and (vy <= 0):
      lastFirstTheta = 2*math.pi - lastFirstTheta
  return lastFirstTheta
  
def distBetweenThetas(theta1, theta2):
  diff = 0
  if theta1 > theta2:
    diff = theta1 - theta2
  else:
    diff = theta2 - theta1
  if diff > math.pi:
    diff = (2 * math.pi) - diff
  return diff

def assignValueIfBetweenRange(value, minn, maxx):
  if value < minn:
    return minn
  if value > maxx:
    return maxx
  return value