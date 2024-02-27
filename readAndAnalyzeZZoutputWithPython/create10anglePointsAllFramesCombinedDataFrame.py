import json
import math

import numpy as np
import pandas as pd

pathToResultFile = 'results_headEmbeddedZebrafishLarva.txt'
plotResultsForQualityControl = False # Set to true for quality control plots

def calculateAngle(vectStart, vectEnd):
  x = vectEnd[0] - vectStart[0]
  y = vectEnd[1] - vectStart[1]
  if x == 0:
    if y > 0:
      heading = math.pi / 2
    else:
      heading = (3 * math.pi) / 2
  else:
    heading = np.arctan(abs(y/x))
    if (x < 0) and (y > 0):
      heading = math.pi - heading
    elif (x < 0) and (y < 0):
      heading = heading + math.pi
    elif (x < 0) and (y == 0):
      heading = math.pi
    elif (x > 0) and (y < 0):
      heading = 2*math.pi - heading
  return heading
  
def calculateTailAngle(angle1, angle2):
  output = angle1 - angle2
  output = (output + 2 * 3.14159265) % (2 * 3.14159265)
  if output > 3.14159265:
    output = output - 2*3.14159265;
  return output

TailX_VideoReferential_All = []
TailY_VideoReferential_All = []
frameNumber_All            = []
numBout_All                = []
allTailAngles_All          = []
allSubsequentAngles_All    = []
with open(pathToResultFile) as video:
  supstruct = json.load(video)
  for numWell in range(0, len(supstruct['wellPoissMouv'])):
    for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
      for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
        bout  = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]
        headX = bout['HeadX']
        headY = bout['HeadY']
        TailX_VideoReferential = bout['TailX_VideoReferential']
        TailY_VideoReferential = bout['TailY_VideoReferential']
        heading = bout['Heading']
        
        allTailAngles       = np.zeros((len(heading), len(TailX_VideoReferential[0])-1))
        allSubsequentAngles = np.zeros((len(heading), len(TailX_VideoReferential[0])-2))
        for i in range(0, len(heading)):
          head = np.array([headX[i], headY[i]])
          for j in range(1, len(TailX_VideoReferential[i])):
            tailPoint     = np.array([TailX_VideoReferential[i][j], TailY_VideoReferential[i][j]])
            allTailAngles[i][j-1] = calculateTailAngle(calculateAngle(head,tailPoint), (heading[i]-math.pi)%(2*math.pi))
          for j in range(1, len(TailX_VideoReferential[i])-1):
            prevTailPoint = np.array([TailX_VideoReferential[i][j-1], TailY_VideoReferential[i][j-1]])
            tailPoint     = np.array([TailX_VideoReferential[i][j], TailY_VideoReferential[i][j]])
            nextTailPoint = np.array([TailX_VideoReferential[i][j+1], TailY_VideoReferential[i][j+1]])
            allSubsequentAngles[i][j-1] = calculateTailAngle(calculateAngle(prevTailPoint, tailPoint), calculateAngle(tailPoint, nextTailPoint))
        
        TailX_VideoReferential_All = TailX_VideoReferential_All + TailX_VideoReferential
        TailY_VideoReferential_All = TailY_VideoReferential_All + TailY_VideoReferential
        allSubsequentAngles_All    = allSubsequentAngles_All    + allSubsequentAngles.tolist()
        allTailAngles_All = allTailAngles_All + allTailAngles.tolist()
        frameNumber_All   = frameNumber_All   + [i for i in range(bout['BoutStart'], bout['BoutEnd'] + 1)]
        numBout_All       = numBout_All       + [numBout for i in range(bout['BoutStart'], bout['BoutEnd'] + 1)]

TailX_VideoReferential_All = np.array(TailX_VideoReferential_All)
TailY_VideoReferential_All = np.array(TailY_VideoReferential_All)
allSubsequentAngles_All    = np.array(allSubsequentAngles_All)
allTailAngles_All          = np.array(allTailAngles_All)
frameNumber_All            = np.array([frameNumber_All]).transpose()
numBout_All                = np.array([numBout_All]).transpose()

df = pd.DataFrame(np.concatenate((frameNumber_All, np.concatenate((numBout_All, np.concatenate((TailX_VideoReferential_All, np.concatenate((TailY_VideoReferential_All, np.concatenate((allTailAngles_All, allSubsequentAngles_All), axis=1)), axis=1)), axis=1)), axis=1)), axis=1), columns=['frameNumber', 'boutNumber'] + ['TailPosX' + str(i) for i in range(1, 11)] + ['TailPosY' + str(i) for i in range(1, 11)] + ['TailAngle' + str(i+1) for i in range(0, len(allTailAngles_All[0]))] + ['SubsequentAngle' + str(i+1) for i in range(0, len(allSubsequentAngles_All[0]))])

df.to_excel('10anglePointsForAllBoutsCombined.xlsx')
df.to_pickle('10anglePointsForAllBoutsCombined.pkl')


if plotResultsForQualityControl:

  import matplotlib.pyplot as plt
  plt.plot(df[['TailAngle' + str(i) for i in range(1, 10)]])
  plt.show()
  
  tailAngleHeatmap = df[['SubsequentAngle' + str(i) for i in range(1, 9)]].values.tolist()
  plt.pcolor(tailAngleHeatmap)
  plt.show()
