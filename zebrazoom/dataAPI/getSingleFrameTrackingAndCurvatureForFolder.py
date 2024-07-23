import os

import cv2
import matplotlib.pyplot as plt

from .plotSingleFrameTrackingPoints import plotSingleFrameTrackingPoints
from .getCurvaturePerBout import getCurvaturePerBout
from .getFPSandPixelSize import getFPSandPixelSize
from .plotCurvatureYaxisApproximate import plotCurvatureYaxisApproximateImplementation


def getSingleFrameTrackingAndCurvatureForFolder(pathToFolder: str):
  for basename in os.listdir(pathToFolder):
    if not basename.endswith('.h5'):
      continue
    filename = os.path.join(pathToFolder, basename)
    outputFolder = os.path.join(pathToFolder, 'output')
    if not os.path.exists(outputFolder):
      os.mkdir(outputFolder)
    _, pixelSize = getFPSandPixelSize(filename)
    plotCurvatureYaxisApproximateImplementation(*getCurvaturePerBout(filename, 0, 0, 0), 1, pixelSize)
    plt.savefig(os.path.join(outputFolder, basename.replace('.h5', '_curvature.png')), dpi=300, bbox_inches='tight')
    plt.close()
    cv2.imwrite(os.path.join(outputFolder, basename.replace('.h5', '.png')), plotSingleFrameTrackingPoints(filename))
