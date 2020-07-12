import sys

from findWells import findWells
from getBackground import getBackground
from getForegroundImage import getForegroundImage
from tracking import tracking
from extractParameters import extractParameters
from createSuperStruct import createSuperStruct
from createValidationVideo import createValidationVideo
from getHyperparameters import getHyperparameters

from sklearn.preprocessing import normalize
import multiprocessing as mp
from multiprocessing import Process
import shutil

import csv

import numpy as np

from getTailTipManual import findTailTipByUserInput
from getTailTipManual import findHeadPositionByUserInput
from headEmbededFrame import headEmbededFrame

def getTailExtremityFirstFrame(pathToVideo, videoName, videoExt, configFile, argv):
  
  videoName = videoName + '.' + videoExt
  
  videoPath = pathToVideo + videoName

  # Getting hyperparameters
  hyperparameters = getHyperparameters(configFile, videoName, videoPath, argv)
  
  frameNumber = hyperparameters["firstFrame"]
  videoNames = [videoName]
  
  if len(argv) > 5:
    for i in range(5, len(argv)):
      if argv[i] == "frameNumber":
        frameNumber = int(argv[i+1])
        break
      else:
        videoNames.append(argv[i])
  
  [frame, thresh1] = headEmbededFrame(videoPath, frameNumber)
  
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
  
  tailTip  = findTailTipByUserInput(frame,hyperparameters)

  for videoN in videoNames:
  
    with open(pathToVideo+'/'+videoN+'.csv', mode='w') as employee_file:
      employee_writer = csv.writer(employee_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      employee_writer.writerow(tailTip)
      
    if hyperparameters["findHeadPositionByUserInput"]:
      headPosition = findHeadPositionByUserInput(frame)
      with open(pathToVideo+'/'+videoN+'HP.csv', mode='w') as employee_file:
        employee_writer = csv.writer(employee_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        employee_writer.writerow(headPosition)
