import numpy as np
import cv2
import math
from zebrazoom.code.trackingFolder.trackingFunctions import assignValueIfBetweenRange

def headTrackingTakeHeadClosestToWellCenter(thresh1, thresh2, blur, erodeSize, minArea, maxArea, frame_width, frame_height):

  x = 0
  y = 0
  xNew = 0
  yNew = 0
  minAreaCur = minArea
  maxAreaCur = maxArea
  while (x == 0) and (minAreaCur > -200):
    contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
      area = cv2.contourArea(contour)
      if (area > minAreaCur) and (area < maxAreaCur):
        M = cv2.moments(contour)
        xNew = int(M['m10']/M['m00'])
        yNew = int(M['m01']/M['m00'])
        distToCenterNew = math.sqrt((xNew-200)**2 + (yNew-200)**2)
        distToCenter    = math.sqrt((x-200)**2    + (y-200)**2)
        # print("distToCenter:",distToCenter," ; distToCenterNew:",distToCenterNew)
        if distToCenterNew < distToCenter:
          x = xNew
          y = yNew
          # print("change realized, new center is:", x, y)
    minAreaCur = minAreaCur - 100
    maxAreaCur = maxAreaCur + 100
    
  halfDiam = 50
  xmin = assignValueIfBetweenRange(x - halfDiam, 0, frame_width-1)
  xmax = assignValueIfBetweenRange(x + halfDiam, 0, frame_height-1)
  ymin = assignValueIfBetweenRange(y - halfDiam, 0, frame_width-1)
  ymax = assignValueIfBetweenRange(y + halfDiam, 0, frame_height-1)
  blur[0:ymin, :]              = 255
  blur[ymax:frame_height-1, :] = 255
  blur[:, 0:xmin]              = 255
  blur[:, xmax:frame_width-1]  = 255
  (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)
      
  return headPosition
