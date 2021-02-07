# If you set the parameter calculateAllTailAngles to 1 in your configuration file, you will get the output data "allTailAngles" and "allTailAnglesSmoothed" for every bout in your result file
# Below is an example of how to plot this output data "allTailAngles" and "allTailAnglesSmoothed"

import json
import matplotlib.pyplot as plt

nameOfVideo = '4wellsZebrafishLarvaeEscapeResponses'

with open('../zebrazoom/ZZoutput/' + nameOfVideo + '/results_' + nameOfVideo + '.txt') as f:
  data = json.load(f)

numWell   = 0
numAnimal = 0
numBout   = 0

allTailAngles         = data['wellPoissMouv'][numWell][numAnimal][numBout]["allTailAngles"]
allTailAnglesSmoothed = data['wellPoissMouv'][numWell][numAnimal][numBout]["allTailAnglesSmoothed"]

for seg in allTailAngles:
  plt.plot(seg)
plt.show()

for seg in allTailAnglesSmoothed:
  plt.plot(seg)
plt.show()

TailAngle_smoothed = data['wellPoissMouv'][numWell][numAnimal][numBout]["TailAngle_smoothed"]
plt.plot(TailAngle_smoothed)
plt.show()

TailAngle_Raw      = data['wellPoissMouv'][numWell][numAnimal][numBout]["TailAngle_Raw"]
plt.plot(TailAngle_Raw)
plt.show()

plt.plot(allTailAnglesSmoothed[len(allTailAnglesSmoothed)-1])
plt.plot(TailAngle_smoothed, '.')
plt.show()

