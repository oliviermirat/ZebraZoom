import numpy as np
import math

def appendPoint(x, y, points):
  curPoint = np.zeros((2, 1))
  curPoint[0] = x
  curPoint[1] = y
  points = np.append(points, curPoint, axis=1)
  return points
  
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
  
def assignValueIfBetweenRangeForDualDirection(value, minn, maxx):
  if value < minn:
    return -1
  if value > maxx:
    return -1
  return value
  
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