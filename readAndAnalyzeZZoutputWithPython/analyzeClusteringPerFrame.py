import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

data = pd.read_excel('classifications.xlsx', index_col=0)

class0Indexes = data.index[data['classification'] == 0].tolist()
class1Indexes = data.index[data['classification'] == 1].tolist()
class2Indexes = data.index[data['classification'] == 2].tolist()

allTailAnglesClass0 = data.loc[class0Indexes, 'tailAngles'].tolist()
allTailAnglesClass1 = data.loc[class1Indexes, 'tailAngles'].tolist()
allTailAnglesClass2 = data.loc[class2Indexes, 'tailAngles'].tolist()

prevNumBout = -10
index = 0
listOfBoutsBeginning = []
for numBout in data['NumBout']:
  if numBout != prevNumBout:
    listOfBoutsBeginning.append(index)
    prevNumBout = numBout
  index = index + 1

if False:
  fig, tabAx = plt.subplots(3, 1)
  tabAx[0].plot([i for i in range(0, len(allTailAnglesClass0))], allTailAnglesClass0)
  tabAx[1].plot([i for i in range(0, len(allTailAnglesClass1))], allTailAnglesClass1)
  tabAx[2].plot([i for i in range(0, len(allTailAnglesClass2))], allTailAnglesClass2)
  plt.show()

if False:  
  plt.plot(class0Indexes, allTailAnglesClass0, 'k.')
  plt.plot(class1Indexes, allTailAnglesClass1, 'g.')
  plt.plot(class2Indexes, allTailAnglesClass2, 'b.')
  plt.plot(listOfBoutsBeginning, [0 for i in range(len(listOfBoutsBeginning))], 'r.')
  plt.show()

if True:
  colors = ['k', 'g', 'b']
  curClass   = 0
  toPlotX    = []
  toPlotY    = []
  for i in range(0, len(data)):
    if data['classification'][i] != curClass:
      toPlotX.append(i)
      toPlotY.append(data['tailAngles'][i])    
      plt.plot(toPlotX, toPlotY, colors[curClass])
      curClass   = int(data['classification'][i])
      toPlotX    = [i]
      toPlotY    = [data['tailAngles'][i]]
    else:
      toPlotX.append(i)
      toPlotY.append(data['tailAngles'][i])
  plt.plot(listOfBoutsBeginning, [0 for i in range(len(listOfBoutsBeginning))], 'r.')
  plt.show()

