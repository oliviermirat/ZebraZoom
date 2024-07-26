import math
import os

import cv2
import numpy as np
import pandas as pd

from .plotSingleFrameTrackingPoints import plotSingleFrameTrackingPoints
from .getCurvaturePerBout import getCurvaturePerBout
from .getFPSandPixelSize import getFPSandPixelSize
from .getDataPerBout import getDataPerBout
from .getSingleFrameDistanceToAxis import getSingleFrameDistanceToAxis


def getSingleFrameTrackingAndDistanceToAxisForFolder(pathToFolder: str):
  for basename in os.listdir(pathToFolder):
    if not basename.endswith('.h5'):
      continue
    filename = os.path.join(pathToFolder, basename)
    outputFolder = os.path.join(pathToFolder, 'output')
    if not os.path.exists(outputFolder):
      os.mkdir(outputFolder)
    frame = plotSingleFrameTrackingPoints(filename)
    # plot the main axis
    heading = getDataPerBout(filename, 0, 0, 0, 'Heading')[0]
    x, y = getDataPerBout(filename, 0, 0, 0, 'HeadPos')[0]
    length = max(frame.shape[:2])  # ensure the line is plotted over the whole frame
    xOffset = length * math.cos(heading)
    yOffset = length * math.sin(heading)
    thickness = 2
    cv2.line(frame, (round(x - xOffset), round(y - yOffset)), (round(x + xOffset), round(y + yOffset)), (0, 0, 255), thickness)
    cv2.imwrite(os.path.join(outputFolder, basename.replace('.h5', '.png')), frame)

    _, pixelSize = getFPSandPixelSize(filename)
    curvature, xTimeValues, yDistanceAlongTheTail = getCurvaturePerBout(filename, 0, 0, 0)
    TailPosX = getDataPerBout(filename, 0, 0, 0, 'TailPosX')
    TailPosY = getDataPerBout(filename, 0, 0, 0, 'TailPosY')
    pd.DataFrame(np.column_stack((np.insert(yDistanceAlongTheTail[:, 0][::-1], 0, 0), TailPosX[0, :], TailPosY[0, :], getSingleFrameDistanceToAxis(filename, pixelSize))), columns=['distanceAlongTheTail', 'TailPosX', 'TailPosY', 'distanceToAxis']).to_excel(os.path.join(outputFolder, basename.replace('.h5', '.xlsx')))
