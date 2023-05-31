import matplotlib.pyplot as plt
import numpy as np


def plotTailAngleHeatmap(tailAngleHeatmap):
  fig = plt.figure(1)
  maxAngle = np.max(np.abs(tailAngleHeatmap))
  plt.pcolor(tailAngleHeatmap[::-1], vmin=-maxAngle, vmax=maxAngle)
  ax = fig.axes
  ax[0].set_xlabel('Frame number')
  ax[0].set_ylabel('Tail angle: Tail base to tail extremity')
  plt.colorbar()
  plt.show()
