from zebrazoom.code.findWells import findWells
from zebrazoom.code.getHyperparameters import getHyperparameters

import csv

import os

from zebrazoom.code.tracking import get_default_tracking_method


def getTailExtremityFirstFrame(pathToVideo, videoName, videoExt, configFile, argv):
  videoName = videoName + '.' + videoExt
  
  videoPath = os.path.join(pathToVideo, videoName)

  # Getting hyperparameters
  [hyperparameters, config] = getHyperparameters(configFile, videoName, videoPath, argv)
  
  frameNumber = hyperparameters["firstFrame"]
  wellNumber = 0
  if hyperparameters["oneWellManuallyChosenTopLeft"]:
    wellPositions = findWells(os.path.join(pathToVideo, videoName), hyperparameters)
  else:
    wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX": hyperparameters["videoWidth"], "lengthY": hyperparameters["videoHeight"]}]
  tracking = get_default_tracking_method()(videoPath, wellPositions, hyperparameters)
  [frame, thresh1] = tracking.headEmbededFrame(frameNumber, wellNumber)

  frame = tracking.getAccentuateFrameForManualPointSelect(frame)
  if hyperparameters["findHeadPositionByUserInput"]:
    with open(os.path.join(pathToVideo, videoName + 'HP.csv'), mode='w') as f:
      writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      writer.writerow(tracking.findHeadPositionByUserInput(frame, frameNumber, wellNumber))

  with open(os.path.join(pathToVideo, videoName + '.csv'), mode='w') as f:
      writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      writer.writerow(tracking.findTailTipByUserInput(frame, frameNumber, wellNumber))
