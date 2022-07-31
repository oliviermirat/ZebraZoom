import numpy as np
import math

def updateBackgroundAtInterval(i, hyperparameters, background, wellPositions, wellNumber, initialCurFrame, firstFrame, trackingHeadTailAllAnimals, frame):
  
  if i % hyperparameters["updateBackgroundAtInterval"] == 0:
    showImages = False
    firstFrameToShow = 10
    if showImages and i > firstFrameToShow:
      import zebrazoom.code.util as util
      util.showFrame(background, title='background before')
    xvalues = [trackingHeadTailAllAnimals[0, i-firstFrame][k][0] for k in range(0, len(trackingHeadTailAllAnimals[0, i-firstFrame]))]
    yvalues = [trackingHeadTailAllAnimals[0, i-firstFrame][k][1] for k in range(0, len(trackingHeadTailAllAnimals[0, i-firstFrame]))]
    xmin = min(xvalues)
    xmax = max(xvalues)
    ymin = min(yvalues)
    ymax = max(yvalues)
    dist = 1 * math.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2)
    xmin = int(xmin - dist) if xmin - dist >= 0 else 0
    xmax = int(xmax + dist) if xmax + dist < len(frame[0]) else len(frame[0]) - 1
    ymin = int(ymin - dist) if ymin - dist >= 0 else 0
    ymax = int(ymax + dist) if ymax + dist < len(frame) else len(frame) - 1
    if xmin != xmax and ymin != ymax:
      partOfBackgroundToSave = background[wellPositions[wellNumber]["topLeftY"]+ymin:wellPositions[wellNumber]["topLeftY"]+ymax, wellPositions[wellNumber]["topLeftX"]+xmin:wellPositions[wellNumber]["topLeftX"]+xmax].copy() # copy ???
      if showImages and i > firstFrameToShow:
        util.showFrame(partOfBackgroundToSave, title='partOfBackgroundToSave')
    background[wellPositions[wellNumber]["topLeftY"]:wellPositions[wellNumber]["topLeftY"]+wellPositions[wellNumber]["lengthY"], wellPositions[wellNumber]["topLeftX"]:wellPositions[wellNumber]["topLeftX"]+wellPositions[wellNumber]["lengthX"]] = initialCurFrame.copy()
    if showImages and i > firstFrameToShow:
      util.showFrame(background, title='background middle')
    if xmin != xmax and ymin != ymax:
      background[wellPositions[wellNumber]["topLeftY"]+ymin:wellPositions[wellNumber]["topLeftY"]+ymax, wellPositions[wellNumber]["topLeftX"]+xmin:wellPositions[wellNumber]["topLeftX"]+xmax] = partOfBackgroundToSave
    if showImages and i > firstFrameToShow:
      util.showFrame(background, title='background after')
  
  return background
