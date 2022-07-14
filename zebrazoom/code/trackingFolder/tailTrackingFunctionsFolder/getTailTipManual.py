import numpy as np
import cv2
from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas
from zebrazoom.code.trackingFolder.trackingFunctions import assignValueIfBetweenRange
import math
from scipy.interpolate import UnivariateSpline
from numpy import linspace
import os.path
import csv
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame


def getAccentuateFrameForManualPointSelect(image, hyperparameters):
  if hyperparameters["accentuateFrameForManualTailExtremityFind"]:
    frame = image.copy()
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
    return frame
  else:
    return image


def findTailTipByUserInput(frame, frameNumber, videoPath, hyperparameters, wellNumber, wellPositions):
  from PyQt5.QtWidgets import QApplication

  import zebrazoom.code.util as util

  plus = 0

  def tailNotStraight(frameWidget):
    nonlocal plus
    plus += 1
    util.setPixmapFromCv(headEmbededFrame(videoPath, frameNumber + plus, wellNumber, wellPositions, hyperparameters)[0], frameWidget, zoomable=True)
  return list(util.getPoint(np.uint8(frame * 255), "Click on tail tip", zoomable=True, extraButtons=(("Tail is not straight", tailNotStraight, False),),
                            dialog=not hasattr(QApplication.instance(), 'window')))

def findHeadPositionByUserInput(frame, frameNumber, videoPath, hyperparameters, wellNumber, wellPositions):
  from PyQt5.QtWidgets import QApplication

  import zebrazoom.code.util as util

  plus = 0

  def tailNotStraight(frameWidget):
    nonlocal plus
    plus += 1
    util.setPixmapFromCv(headEmbededFrame(videoPath, frameNumber + plus, wellNumber, wellPositions, hyperparameters)[0], frameWidget, zoomable=True)
  return list(util.getPoint(np.uint8(frame * 255), "Click on the base of the tail", zoomable=True, extraButtons=(("Tail is not straight", tailNotStraight, False),),
                            dialog=not hasattr(QApplication.instance(), 'window')))


def getTailTipByFileSaved(hyperparameters,videoPath):
  ix = -1
  iy = -1
  with open(videoPath+'.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
      if len(row):
        ix = row[0]
        iy = row[1]
  return [int(ix),int(iy)]

def getHeadPositionByFileSaved(videoPath):
  ix = -1
  iy = -1
  with open(videoPath+'HP.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
      if len(row):
        ix = row[0]
        iy = row[1]
  return [int(ix),int(iy)]
  