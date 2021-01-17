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
  
# ix,  iy  = -1,-1
# ix2, iy2 = -1,-1

# mouse callback function
# def getXYCoordinates(event,x,y,flags,param):
  # global ix,iy
  # if event == cv2.EVENT_LBUTTONDOWN:
    # ix,iy = x,y
    
# def getXYCoordinates2(event,x2,y2,flags,param):
  # global ix2,iy2
  # if event == cv2.EVENT_LBUTTONDOWN:
    # ix2,iy2 = x2,y2

def findTailTipByUserInput(frame, frameNumber, videoPath, hyperparameters):
  # global ix 
  # ix = -1
  # img = np.zeros((512,512,3), np.uint8)
  # cv2.namedWindow('Click on tail tip')
  # cv2.setMouseCallback('Click on tail tip',getXYCoordinates)
  # print("ix:", ix)
  # while(ix == -1):
    # cv2.imshow('Click on tail tip',frame)
    # k = cv2.waitKey(20) & 0xFF
    # if k == 27:
      # break
    # elif k == ord('a'):
      # print("yeah:",ix,iy)
  # cv2.destroyAllWindows()
  # return [ix,iy]
  
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
      [frame, thresh1] = headEmbededFrame(videoPath, frameNumber + plus)
      frame = cv2.rectangle(frame, (0, 0), (250, 29), (255, 255, 255), -1)
      cv2.putText(frame,'Click any key if the tail is', (1, 10), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cv2.putText(frame,'not straight on this image', (1, 22), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cvui.imshow(WINDOW_NAME, frame)
      plus = plus + 1
  # cv2.destroyAllWindows()
  cv2.destroyWindow(WINDOW_NAME)
  return [cursor.x, cursor.y]
  
def findHeadPositionByUserInput(frame, frameNumber, videoPath):
  # img = np.zeros((512,512,3), np.uint8)
  # cv2.namedWindow('Click on the base of the tail')
  # cv2.setMouseCallback('Click on the base of the tail',getXYCoordinates2)
  # while(ix2 == -1):
    # cv2.imshow('Click on the base of the tail',frame)
    # k = cv2.waitKey(20) & 0xFF
    # if k == 27:
      # break
    # elif k == ord('a'):
      # print("yeah:",ix2,iy2)
  # cv2.destroyAllWindows()
  # return [ix2,iy2]
  
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
      [frame, thresh1] = headEmbededFrame(videoPath, frameNumber + plus)
      frame = cv2.rectangle(frame, (0, 0), (250, 29), (255, 255, 255), -1)
      cv2.putText(frame,'Click any key if the tail is', (1, 10), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cv2.putText(frame,'not straight on this image', (1, 22), font, 0.5, (0, 150, 0), 1, cv2.LINE_AA)
      cvui.imshow(WINDOW_NAME, frame)
      plus = plus + 1
  # cv2.destroyAllWindows()
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
  