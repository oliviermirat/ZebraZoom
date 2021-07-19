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

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import findTailTipByUserInput
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import findHeadPositionByUserInput
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame

def getTailExtremityFirstFrame(pathToVideo, videoName, videoExt, configFile, argv):
  
  videoName = videoName + '.' + videoExt
  
  videoPath = pathToVideo + videoName

  # Getting hyperparameters
  [hyperparameters, config] = getHyperparameters(configFile, videoName, videoPath, argv)
  
  frameNumber = hyperparameters["firstFrame"]
  videoNames = [videoName]
  
  if len(argv) > 5:
    for i in range(5, len(argv)):
      if argv[i] == "frameNumber":
        frameNumber = int(argv[i+1])
        break
      else:
        videoNames.append(argv[i])
  
  [frame, thresh1] = headEmbededFrame(videoPath, frameNumber, hyperparameters)
  
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
  
  tailTip  = findTailTipByUserInput(frame, frameNumber, videoPath, hyperparameters)

  for videoN in videoNames:
  
    with open(pathToVideo+'/'+videoN+'.csv', mode='w') as employee_file:
      employee_writer = csv.writer(employee_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      employee_writer.writerow(tailTip)
      
    if hyperparameters["findHeadPositionByUserInput"]:
      headPosition = findHeadPositionByUserInput(frame, frameNumber, videoPath)
      with open(pathToVideo+'/'+videoN+'HP.csv', mode='w') as employee_file:
        employee_writer = csv.writer(employee_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        employee_writer.writerow(headPosition)
