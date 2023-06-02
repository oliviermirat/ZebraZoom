import matplotlib.pyplot as plt
import numpy as np


def plotTailAngleHeatmap(tailAngleHeatmap: list, startFrame: int, tailLength: float, videoFPS: float, videoPixelSize: float):
  fig = plt.figure(1)
  maxAngle = np.nanmax(np.abs(tailAngleHeatmap))
  plt.pcolor(tailAngleHeatmap[::-1], vmin=-maxAngle, vmax=maxAngle)
  ax, *_ = fig.axes
  ax.set_xlabel('Time (in seconds)')
  ax.set_ylabel('Tail angle: Tail base to tail extremity (in mm)')
  ax.xaxis.set_major_formatter(lambda x, pos: f'{(x + startFrame) / videoFPS:.2f}')
  yStepSize = tailLength / len(tailAngleHeatmap)
  ax.yaxis.set_major_formatter(lambda y, pos: f'{y * yStepSize * videoPixelSize:.2f}')
  plt.colorbar()
  plt.show()
