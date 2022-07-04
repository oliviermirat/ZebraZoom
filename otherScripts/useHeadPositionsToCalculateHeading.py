import json
import numpy as np
import matplotlib.pyplot as plt
import math

with open('results_4wellsZebrafishLarvaeEscapeResponses.txt') as f:
  supstruct = json.load(f)

headX = supstruct['wellPoissMouv'][0][0][0]['HeadX']
headY = supstruct['wellPoissMouv'][0][0][0]['HeadY']
TailAngle_smoothed = supstruct['wellPoissMouv'][0][0][0]['TailAngle_smoothed']
angle         = []
realTailAngle = []

step = 5
for i in range(0, len(headX)-1, step):
  if i+step < len(headX):
    vectX = float(headX[i+step] - headX[i])
    vectY = float(headY[i+step] - headY[i])
    if vectX > 0:
      ang   = np.arctan(vectY / vectX)
    elif vectX < 0:
      ang   = np.arctan(vectY / vectX) + math.pi
    else:
      if vectY > 0:
        ang = math.pi / 2
      elif vectY < 0:
        ang = - math.pi / 2
      else:
        ang = 0
  angle.append(np.arctan(vectY / vectX) if vectX else math.pi/2)
  realTailAngle.append(TailAngle_smoothed[i + int(step/2)])

plt.plot(angle)
plt.plot([-r for r in realTailAngle])
plt.show()
