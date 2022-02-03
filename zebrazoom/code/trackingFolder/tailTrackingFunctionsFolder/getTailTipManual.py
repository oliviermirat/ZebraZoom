import numpy as np
import cv2
import cvui
from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas
from zebrazoom.code.trackingFolder.trackingFunctions import assignValueIfBetweenRange
import math
from scipy.interpolate import UnivariateSpline
from numpy import linspace
import os.path
import csv
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame

from PyQt6.QtWidgets import QApplication

import zebrazoom.code.util as util


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


def _findTailTipByUserInputQt(frame, frameNumber, videoPath, hyperparameters):
  plus = 0

  def tailNotStraight(frameWidget):
    nonlocal plus
    plus += 1
    util.setPixmapFromCv(headEmbededFrame(videoPath, frameNumber + plus, hyperparameters)[0], frameWidget)
  return list(util.getPoint(np.uint8(frame * 255), "Click on tail tip", extraButtons=(("Tail is not straight", tailNotStraight, False),)))


def findTailTipByUserInput(frame, frameNumber, videoPath, hyperparameters):
  if QApplication.instance() is not None:
    return _findTailTipByUserInputQt(frame, frameNumber, videoPath, hyperparameters)

  WINDOW_NAME = "Click on tail tip"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0, 0)
  
  font = cv2.FONT_HERSHEY_SIMPLEX
  frame = cv2.rectangle(frame, (0, 0), (250, 29), (255, 255, 255), -1)
  cv2.putText(frame,'Click any key if the tail is', (1, 10), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
  cv2.putText(frame,'not straight on this image', (1, 22), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
  
  cvui.imshow(WINDOW_NAME, frame)
  plus = 1
  while not(cvui.mouse(WINDOW_NAME, cvui.CLICK)):
    cursor = cvui.mouse(WINDOW_NAME)
    if cv2.waitKey(20) != -1:
      [frame, thresh1] = headEmbededFrame(videoPath, frameNumber + plus, hyperparameters)
      frame = cv2.rectangle(frame, (0, 0), (250, 29), (255, 255, 255), -1)
      cv2.putText(frame,'Click any key if the tail is', (1, 10), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cv2.putText(frame,'not straight on this image', (1, 22), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cvui.imshow(WINDOW_NAME, frame)
      plus = plus + 1
  
  cv2.destroyWindow(WINDOW_NAME)
  return [cursor.x, cursor.y]


def _findHeadPositionByUserInputQt(frame, frameNumber, videoPath, hyperparameters):
  plus = 0

  def tailNotStraight(frameWidget):
    nonlocal plus
    plus += 1
    util.setPixmapFromCv(headEmbededFrame(videoPath, frameNumber + plus, hyperparameters)[0], frameWidget)
  return list(util.getPoint(np.uint8(frame * 255), "Click on the base of the tail", extraButtons=(("Tail is not straight", tailNotStraight, False),)))


def findHeadPositionByUserInput(frame, frameNumber, videoPath, hyperparameters={}):
  if QApplication.instance() is not None:
    return _findHeadPositionByUserInputQt(frame, frameNumber, videoPath, hyperparameters)

  WINDOW_NAME = "Click on the base of the tail"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  font = cv2.FONT_HERSHEY_SIMPLEX
  plus = 1
  frame = cv2.rectangle(frame, (0, 0), (250, 29), (255, 255, 255), -1) 
  cv2.putText(frame,'Click any key if the tail is', (1, 10), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
  cv2.putText(frame,'not straight on this image', (1, 22), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
  cvui.imshow(WINDOW_NAME, frame)
  while not(cvui.mouse(WINDOW_NAME, cvui.CLICK)):
    cursor = cvui.mouse(WINDOW_NAME)
    if cv2.waitKey(20) != -1:
      [frame, thresh1] = headEmbededFrame(videoPath, frameNumber + plus, hyperparameters)
      frame = cv2.rectangle(frame, (0, 0), (250, 29), (255, 255, 255), -1)
      cv2.putText(frame,'Click any key if the tail is', (1, 10), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cv2.putText(frame,'not straight on this image', (1, 22), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cvui.imshow(WINDOW_NAME, frame)
      plus = plus + 1
  
  cv2.destroyWindow(WINDOW_NAME)
  return [cursor.x, cursor.y]

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
  