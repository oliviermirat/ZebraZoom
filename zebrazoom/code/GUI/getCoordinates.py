import numpy as np
import cv2
import cvui
from zebrazoom.code.resizeImageTooLarge import resizeImageTooLarge

def getXYCoordinates(frame, text):
  
  frame2 = frame.copy()
  [frame2, getRealValueCoefX, getRealValueCoefY, horizontal, vertical] = resizeImageTooLarge(frame2, True, 0.85)
  
  WINDOW_NAME = text
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  cvui.imshow(WINDOW_NAME, frame2)
  while not(cvui.mouse(cvui.CLICK)):
    cursor = cvui.mouse()
    if cv2.waitKey(20) == 27:
      break
  cv2.destroyAllWindows()

  return [int(getRealValueCoefX * cursor.x), int(getRealValueCoefY * cursor.y)]

def findWellLeft(frame):
  [x, y] = getXYCoordinates(frame, "Click on left border")
  return [x, y]

def findWellRight(frame):
  [x, y] = getXYCoordinates(frame, "Click on right border")
  return [x, y]

def findHeadCenter(frame):
  [x, y] = getXYCoordinates(frame, "Click on a head center")
  return [x, y]

def findBodyExtremity(frame):
  [x, y] = getXYCoordinates(frame, "Click on the tip of the tail of the same zebrafish")
  return [x, y]
