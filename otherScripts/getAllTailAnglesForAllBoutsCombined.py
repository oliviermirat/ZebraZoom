# from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import json
import math

import json
with open('../zebrazoom/ZZoutput/4wellsZebrafishLarvaeEscapeResponses/results_4wellsZebrafishLarvaeEscapeResponses.txt') as f:
  dataRef = json.load(f)

numWell   = 0
numAnimal = 0

tailAngleFinal = []
xaxisFinal = []

graphScaling = 1

if "firstFrame" in dataRef and "lastFrame" in dataRef:
  begMove = 0
  endMove = dataRef["wellPoissMouv"][numWell][numAnimal][0]["BoutStart"]
  xaxis     = [i for i in range(begMove, endMove)]
  tailAngle = [0 for i in range(begMove, endMove)]
  tailAngleFinal = tailAngleFinal + tailAngle
  xaxisFinal = xaxisFinal + xaxis
  
for numMouv in range(0, len(dataRef["wellPoissMouv"][numWell][numAnimal])):
  tailAngle = dataRef["wellPoissMouv"][numWell][numAnimal][numMouv]["TailAngle_smoothed"].copy()
  for ind,val in enumerate(tailAngle):
    tailAngle[ind]=tailAngle[ind]*(180/(math.pi))
  begMove = dataRef["wellPoissMouv"][numWell][numAnimal][numMouv]["BoutStart"]
  endMove = begMove + len(tailAngle)
  xaxis = [i for i in range(begMove-1,endMove+1)]
  tailAngle.append(0)
  tailAngle.insert(0, 0)
  tailAngleFinal = tailAngleFinal + tailAngle
  xaxisFinal = xaxisFinal + xaxis

if "firstFrame" in dataRef and "lastFrame" in dataRef:
  begMove = endMove
  endMove = dataRef["lastFrame"] - 1
  xaxis     = [i for i in range(begMove, endMove)]
  tailAngle = [0 for i in range(begMove, endMove)]
  tailAngleFinal = tailAngleFinal + tailAngle
  xaxisFinal = xaxisFinal + xaxis

if "fps" in dataRef:
  plt.plot([xaxisFinalVal / dataRef["fps"] for xaxisFinalVal in xaxisFinal], tailAngleFinal)
else:
  plt.plot(xaxisFinal, tailAngleFinal)

if not(graphScaling):
  plt.ylim(-140, 140)

if "firstFrame" in dataRef and "lastFrame" in dataRef:
  if "fps" in dataRef:
    plt.xlim(dataRef["firstFrame"] / dataRef["fps"], dataRef["lastFrame"] / dataRef["fps"])
  else:
    plt.xlim(dataRef["firstFrame"], dataRef["lastFrame"])

plt.show()
