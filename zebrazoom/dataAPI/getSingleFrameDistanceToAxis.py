import math

import numpy as np

from .getDataPerBout import getDataPerBout


def _distanceBetweenPointAndLine(p1, p2, p3, pixelSize):  # p1 and p2 define the line, p3 is the point
  x0, y0 = p3
  x1, y1 = p1
  x2, y2 = p2
  return -pixelSize * ((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def getSingleFrameDistanceToAxis(videoName: str, pixelSize):
  heading = getDataPerBout(videoName, 0, 0, 0, 'Heading')[0]
  x1, y1 = getDataPerBout(videoName, 0, 0, 0, 'HeadPos')[0]
  x2 = x1 + 1000 * math.cos(heading)
  y2 = y1 + 1000 * math.sin(heading)
  return [_distanceBetweenPointAndLine((x1, y1), (x2, y2), pos, pixelSize) for pos in zip(getDataPerBout(videoName, 0, 0, 0, 'TailPosX')[0], getDataPerBout(videoName, 0, 0, 0, 'TailPosY')[0])]
