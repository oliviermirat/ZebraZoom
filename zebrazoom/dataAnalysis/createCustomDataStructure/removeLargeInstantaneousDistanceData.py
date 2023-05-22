import json
import matplotlib.pyplot as plt
import cv2
import numpy as np
import math
import pandas as pd
import os

from PyQt5.QtWidgets import QFileDialog


def removeLargeInstantaneousDistanceData(ZZoutputFolder, maxDistance):

  pathToResultFolder =  QFileDialog.getExistingDirectory(caption='Choose the result folder for which an excel file should be generated', directory=ZZoutputFolder)
  if not pathToResultFolder:
    return

  videoName = os.path.basename(os.path.normpath(pathToResultFolder))
  
  numberOfWells       = 0
  totalNumberOfFrames = 0
  
  with open(os.path.join(pathToResultFolder, 'results_' + videoName + '.txt')) as video:
  
    supstruct = json.load(video)
    
    numberOfWells = len(supstruct['wellPoissMouv'])
    firstFrame = 0
    lastFrame  = 0
    if ('lastFrame' in supstruct) and ('firstFrame' in supstruct):
      totalNumberOfFrames = supstruct['lastFrame'] - supstruct['firstFrame'] + 1
      firstFrame = int(supstruct['firstFrame'])
      lastFrame  = int(supstruct['lastFrame'])
    else:
      raise NameError('firstFrame and lastFrame are not in the superstructure results file!')
    
    print("totalNumberOfFrames: ", totalNumberOfFrames)
    
    for numWell in range(0, len(supstruct['wellPoissMouv'])):  
      for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
        for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
          bout = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]
          HeadX = bout['HeadX']
          HeadY = bout['HeadY']
          for i in range(0, len(HeadX)-1):
            if (HeadX[i] != float('nan') and HeadY[i] != float('nan')):
              distance = math.sqrt((HeadX[i] - HeadX[i+1])**2 + (HeadY[i] - HeadY[i+1])**2)
              if (distance > maxDistance):
                HeadX[i + 1] = float('nan')
                HeadY[i + 1] = float('nan')
          supstruct['wellPoissMouv'][numWell][numAnimal][numBout]['HeadX'] = HeadX
          supstruct['wellPoissMouv'][numWell][numAnimal][numBout]['HeadY'] = HeadY
          
  with open(os.path.join(pathToResultFolder, 'results_' + videoName + '.txt'), 'w') as outfile:
    json.dump(supstruct, outfile)
