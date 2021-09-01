import numpy as np
import math
import cvui
import cv2

def calculateAngle(xStart, yStart, xEnd, yEnd):
  vx = xEnd - xStart
  vy = yEnd - yStart
  if vx == 0:
    if vy > 0:
      lastFirstTheta = math.pi/2
    else:
      lastFirstTheta = (3*math.pi)/2
  else:
    lastFirstTheta = np.arctan(abs(vy/vx))
    if (vx < 0) and (vy >= 0):
      lastFirstTheta = math.pi - lastFirstTheta
    elif (vx < 0) and (vy <= 0):
      lastFirstTheta = lastFirstTheta + math.pi
    elif (vx > 0) and (vy <= 0):
      lastFirstTheta = 2*math.pi - lastFirstTheta
  return lastFirstTheta
  
def distBetweenThetas(theta1, theta2):
  diff = 0
  if theta1 > theta2:
    diff = theta1 - theta2
  else:
    diff = theta2 - theta1
  if diff > math.pi:
    diff = (2 * math.pi) - diff
  return diff

def assignValueIfBetweenRange(value, minn, maxx):
  if value < minn:
    return minn
  if value > maxx:
    return maxx
  return value

def addBlackLineToImgSetParameters(hyperparameters, frame):

  frame2 = frame.copy()
  # frame2 = 255 - frame2
  quartileChose = hyperparameters["outputValidationVideoContrastImprovementQuartile"]
  lowVal  = int(np.quantile(frame2, quartileChose))
  highVal = int(np.quantile(frame2, 1 - quartileChose))
  frame2[frame2 < lowVal]  = lowVal
  frame2[frame2 > highVal] = highVal
  frame2 = frame2 - lowVal
  mult  = np.max(frame2)
  frame2 = frame2 * (255/mult)
  frame2 = frame2.astype('uint8')
  
  WINDOW_NAME = "Click on beginning of segment to set to black pixels"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0, 0)
  cvui.imshow(WINDOW_NAME, frame2)
  plus = 1
  while not(cvui.mouse(WINDOW_NAME, cvui.CLICK)):
    cursor = cvui.mouse(WINDOW_NAME)
    if cv2.waitKey(20) != -1:
      cvui.imshow(WINDOW_NAME, frame2)
      plus = plus + 1
  cv2.destroyWindow(WINDOW_NAME)
  startPoint = [cursor.x, cursor.y]
  
  WINDOW_NAME = "Click on the end of the segment to set to black pixels"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0, 0)
  cvui.imshow(WINDOW_NAME, frame2)
  plus = 1
  while not(cvui.mouse(WINDOW_NAME, cvui.CLICK)):
    cursor = cvui.mouse(WINDOW_NAME)
    frame3 = frame2.copy()
    frame3 = cv2.line(frame3, (startPoint[0], startPoint[1]), (cursor.x, cursor.y), (255, 255, 255), hyperparameters["addBlackLineToImg_Width"])
    cvui.imshow(WINDOW_NAME, frame3)
    plus = plus + 1
    cv2.waitKey(20)
    del frame3
  cv2.destroyWindow(WINDOW_NAME)
  endPoint = [cursor.x, cursor.y]  
  
  hyperparameters["imagePreProcessMethod"]     = ["setImageLineToBlack"]
  hyperparameters["imagePreProcessParameters"] = [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], hyperparameters["addBlackLineToImg_Width"]]]
  
  print('addBlackLineToImg_Width is at', hyperparameters["addBlackLineToImg_Width"],', so in the configuration file, "imagePreProcessMethod" has just been set to ["setImageLineToBlack"] and "imagePreProcessParameters" has just been set to', str(hyperparameters["imagePreProcessParameters"]))

  return hyperparameters
