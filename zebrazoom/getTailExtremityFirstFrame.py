from zebrazoom.code.findWells import findWells
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.createSuperStruct import createSuperStruct
from zebrazoom.code.createValidationVideo import createValidationVideo
from zebrazoom.code.getHyperparameters import getHyperparameters

from sklearn.preprocessing import normalize
import multiprocessing as mp
from multiprocessing import Process
import shutil

import csv

import numpy as np
import os

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import findTailTipByUserInput
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import findHeadPositionByUserInput
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame

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
  [frame, thresh1] = headEmbededFrame(videoPath, frameNumber, wellNumber, wellPositions, hyperparameters)
  
  if hyperparameters["accentuateFrameForManualTailExtremityFind"]:
    quartileChose = 0.01
    lowVal  = int(np.quantile(frame, quartileChose))
    highVal = int(np.quantile(frame, 1 - quartileChose))
    frame[frame < lowVal]  = lowVal
    frame[frame > highVal] = highVal
    frame = frame - lowVal
    mult  = np.max(frame)
    frame = frame * (255/mult)
    frame = frame.astype(int)
    frame = (frame / np.linalg.norm(frame))*255

  if hyperparameters["findHeadPositionByUserInput"]:
    with open(os.path.join(pathToVideo, videoName + 'HP.csv'), mode='w') as f:
      writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      writer.writerow(findHeadPositionByUserInput(frame, frameNumber, videoPath, hyperparameters, wellNumber, wellPositions))

  with open(os.path.join(pathToVideo, videoName + '.csv'), mode='w') as f:
      writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      writer.writerow(findTailTipByUserInput(frame, frameNumber, videoPath, hyperparameters, wellNumber, wellPositions))
