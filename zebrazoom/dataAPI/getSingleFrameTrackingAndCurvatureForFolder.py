import os

import cv2
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from .plotSingleFrameTrackingPoints import plotSingleFrameTrackingPoints
from .getCurvaturePerBout import getCurvaturePerBout
from .getFPSandPixelSize import getFPSandPixelSize
from .plotCurvatureYaxisApproximate import plotCurvatureYaxisApproximateImplementation
from .getDataPerBout import getDataPerBout

def getSingleFrameTrackingAndCurvatureForFolder(pathToFolder: str):
  for basename in os.listdir(pathToFolder):
    if not basename.endswith('.h5'):
      continue
    filename = os.path.join(pathToFolder, basename)
    outputFolder = os.path.join(pathToFolder, 'output')
    if not os.path.exists(outputFolder):
      os.mkdir(outputFolder)
    _, pixelSize = getFPSandPixelSize(filename)
    [curvature, xTimeValues, yDistanceAlongTheTail] = getCurvaturePerBout(filename, 0, 0, 0)
    plotCurvatureYaxisApproximateImplementation(*[curvature, xTimeValues, yDistanceAlongTheTail], 1, pixelSize)
    plt.savefig(os.path.join(outputFolder, basename.replace('.h5', '_curvature.png')), dpi=300, bbox_inches='tight')
    plt.close()
    cv2.imwrite(os.path.join(outputFolder, basename.replace('.h5', '.png')), plotSingleFrameTrackingPoints(filename))
    
    TailPosX = getDataPerBout(filename, 0, 0, 0, 'TailPosX')
    TailPosY = getDataPerBout(filename, 0, 0, 0, 'TailPosY')
    
    pd.DataFrame(np.column_stack((np.insert(yDistanceAlongTheTail[:, 0][::-1], 0, 0), TailPosX[0, :], TailPosY[0, :], np.insert(curvature[:, 0][::-1], 0, 0))), columns=['distanceAlongTheTail', 'TailPosX', 'TailPosY', 'curvature']).to_excel(os.path.join(outputFolder, basename.replace('.h5', '.xlsx')))
    