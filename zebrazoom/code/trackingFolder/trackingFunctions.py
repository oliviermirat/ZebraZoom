import numpy as np
import math
import json
import cv2
import os

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

def addBlackLineToImgSetParameters(hyperparameters, frame, videoName):
  import zebrazoom.code.util as util

  hyperparametersToSave = {"addBlackLineToImg_Width": 0}
  
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
  
  addNewSegment  = True
  
  while addNewSegment:
    
    startPoint = util.getPoint(frame2, "Click on beginning of segment to set to black pixels", dialog=True)
    endPoint = util.getLine(frame2, "Click on the end of the segment to set to black pixels", hyperparameters["addBlackLineToImg_Width"], startPoint)
    
    if not("imagePreProcessMethod" in hyperparameters) or type(hyperparameters["imagePreProcessMethod"]) == int or len(hyperparameters["imagePreProcessMethod"]) == 0:
      hyperparameters["imagePreProcessMethod"]     = ["setImageLineToBlack"]
      hyperparameters["imagePreProcessParameters"] = [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], hyperparameters["addBlackLineToImg_Width"]]]
      hyperparametersToSave["imagePreProcessMethod"]     = ["setImageLineToBlack"]
      hyperparametersToSave["imagePreProcessParameters"] = [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], hyperparameters["addBlackLineToImg_Width"]]]
    else:
      hyperparameters["imagePreProcessMethod"] = hyperparameters["imagePreProcessMethod"] + ["setImageLineToBlack"]
      hyperparameters["imagePreProcessParameters"] += [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], hyperparameters["addBlackLineToImg_Width"]]]
      hyperparametersToSave["imagePreProcessMethod"]     += ["setImageLineToBlack"]
      hyperparametersToSave["imagePreProcessParameters"] += [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], hyperparameters["addBlackLineToImg_Width"]]]
    
    print('addBlackLineToImg_Width is at', hyperparameters["addBlackLineToImg_Width"],', so in the configuration file, "imagePreProcessMethod" has just been set to ["setImageLineToBlack"] and "imagePreProcessParameters" has just been set to', str(hyperparameters["imagePreProcessParameters"]))

    frame2 = cv2.line(frame2, (startPoint[0], startPoint[1]), (endPoint[0], endPoint[1]), (255, 255, 255), hyperparameters["addBlackLineToImg_Width"])

    def doneAddingSegments():
      nonlocal addNewSegment
      addNewSegment = False
    buttons = (("I want to add another segment.", None), ("I've added enough segments.", doneAddingSegments))
    util.showFrame(frame2, title="Do you want to add another segment?", buttons=buttons)
  
  with open(os.path.join(os.path.join(hyperparameters["outputFolder"], videoName), 'parametersToAddToConfigFileForBlackLine.json'), 'w') as outfile:
    json.dump(hyperparametersToSave, outfile)
  
  return hyperparameters
