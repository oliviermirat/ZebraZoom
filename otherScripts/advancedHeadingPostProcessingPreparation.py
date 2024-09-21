import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import shutil
import math
import os

videoNameOri = "RAW-DATA_2024_09_11-09_56_23"
videoName    = "RAW-DATA_copy_2024_09_11-09_56_23"
ZZoutputPath = os.path.join('zebrazoom', 'ZZoutput')
windowNbFrames = 30

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

def putAngleInOtherAngleReferential(firstAngle, secondAngle):
  secondAngleInFirstReferential = secondAngle - firstAngle
  # if abs(secondAngleInFirstReferential) > math.pi:
    # secondAngleInFirstReferential = (secondAngleInFirstReferential + 2 * math.pi) % (2 * math.pi)
    # if abs(secondAngleInFirstReferential) > math.pi:
      # secondAngleInFirstReferential = secondAngleInFirstReferential - 2 * math.pi
  # return secondAngleInFirstReferential
  
  return abs(math.pi - ((secondAngleInFirstReferential + 2 * math.pi) % (2 * math.pi)))
  # return (math.pi - ((secondAngleInFirstReferential + 2 * math.pi) % (2 * math.pi)))


def calculateListOfSurroundingAngles(frameNumber, headingValue, xPos, yPos, windowNbFrames, minDist):

  listOfSurroundingAngles    = []
  listOfSurroundingAnglesOri = []

  back = 1
  while frameNumber - back >= 0 and len(listOfSurroundingAngles) < windowNbFrames:
    xPosAround = headPos[frameNumber - back][0]
    yPosAround = headPos[frameNumber - back][1]
    if math.sqrt((xPosAround - xPos) ** 2 + (yPosAround - yPos) ** 2) >= minDist:
      listOfSurroundingAngles    = [putAngleInOtherAngleReferential(headingValue, calculateAngle(xPosAround, yPosAround, xPos, yPos))] + listOfSurroundingAngles
      listOfSurroundingAnglesOri = [calculateAngle(xPosAround, yPosAround, xPos, yPos)] + listOfSurroundingAnglesOri
    back += 1
  if len(listOfSurroundingAngles) < windowNbFrames:
    while len(listOfSurroundingAngles) < windowNbFrames:
      listOfSurroundingAngles    = [listOfSurroundingAngles[0] if len(listOfSurroundingAngles) else 0] + listOfSurroundingAngles
      listOfSurroundingAnglesOri = [listOfSurroundingAnglesOri[0] if len(listOfSurroundingAnglesOri) else 0] + listOfSurroundingAnglesOri

  fwd = 1
  while frameNumber + fwd < len(heading) and len(listOfSurroundingAngles) < 2 * windowNbFrames:
    xPosAround = headPos[frameNumber + fwd][0]
    yPosAround = headPos[frameNumber + fwd][1]
    if math.sqrt((xPosAround - xPos) ** 2 + (yPosAround - yPos) ** 2) >= minDist:
      listOfSurroundingAngles.append(putAngleInOtherAngleReferential(headingValue, calculateAngle(xPos, yPos, xPosAround, yPosAround)))
      listOfSurroundingAnglesOri.append(calculateAngle(xPos, yPos, xPosAround, yPosAround))
    fwd += 1
  if len(listOfSurroundingAngles) < 2 * windowNbFrames:
    while len(listOfSurroundingAngles) < 2 * windowNbFrames:
      listOfSurroundingAngles.append(listOfSurroundingAngles[len(listOfSurroundingAngles) - 1] if len(listOfSurroundingAngles) else 0)
      listOfSurroundingAnglesOri.append(listOfSurroundingAnglesOri[len(listOfSurroundingAnglesOri) - 1] if len(listOfSurroundingAnglesOri) else 0)
  
  return [listOfSurroundingAngles, listOfSurroundingAnglesOri]


# videoName = dataAPI.copyHdf5(videoName)


shutil.copyfile(os.path.join(ZZoutputPath, videoNameOri + ".h5"), os.path.join(ZZoutputPath, videoName + ".h5"))


[videoFPS, videoPixelSize] = dataAPI.getFPSandPixelSize(videoName)

numWell   = 0
numAnimal = 0
startTimeInSeconds = 0
endTimeInSeconds = 600 #45200 / videoFPS

minDist = 10

heading = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, 'Heading')

headPos = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, 'HeadPos')

listForEachFrame    = [[0 for framesAroundNumber in range(-windowNbFrames, windowNbFrames)]] * len(heading)
listForEachFrameOri = [[0 for framesAroundNumber in range(-windowNbFrames, windowNbFrames)]] * len(heading)

for frameNumber in range(len(heading)):
  
  if frameNumber % 50 == 0:
    print(frameNumber, "out of:", len(heading))
  
  if frameNumber - windowNbFrames >= 0 and frameNumber + windowNbFrames < len(heading):
    headingValue    = heading[frameNumber]
    xPos = headPos[frameNumber][0]
    yPos = headPos[frameNumber][1]
    
    [listOfSurroundingAngles, listOfSurroundingAnglesOri] = calculateListOfSurroundingAngles(frameNumber, headingValue, xPos, yPos, windowNbFrames, minDist)
    
    listForEachFrame[frameNumber]    = listOfSurroundingAngles
    listForEachFrameOri[frameNumber] = listOfSurroundingAnglesOri

###

data = np.array(listForEachFrame)
dataOri = np.array(listForEachFrameOri)

intergralOutlierSearch = True
if not(intergralOutlierSearch):
  mean_per_column = np.mean(data, axis=0)
  std_per_column = np.std(data, axis=0)
  threshold = 2
  outliers = (np.abs(data - mean_per_column) > threshold * std_per_column)
  nbOutliersPerLine = [np.sum(outliers[i]) for i in range(len(outliers))]
  # nbOutliersPerLine = [np.sum(outliers[i][:30]) for i in range(len(outliers))]
else:
  sumError = np.sum(data, axis=1)
  mean_Error = np.mean(sumError)
  std_Error  = np.std(sumError)
  minValue   = mean_Error - 2 * std_Error
  print("mean_Error:", mean_Error, "; std_Error:", std_Error)
  print("minValue:", minValue)
  print("less strict:", mean_Error - std_Error)
  outliers = (sumError < minValue)
  nbOutliersPerLine = outliers.copy()

headingC = heading.copy()
change = [0] * len(heading)

if not(intergralOutlierSearch):
  maxOutliersPerLine = 28 #10 #20 #30
else:
  maxOutliersPerLine = 0

allOutliers = []
for idx, nbOutliers in enumerate(nbOutliersPerLine):
  if nbOutliers > maxOutliersPerLine:
    allOutliers.append(idx)
    
    [listOfSurroundingAngles, listOfSurroundingAnglesOri] = calculateListOfSurroundingAngles(idx, (heading[idx] + math.pi) % (2 * math.pi), headPos[idx][0], headPos[idx][1], windowNbFrames, minDist)
    sumErrorLoc = np.sum(listOfSurroundingAngles)
    if (sumErrorLoc > mean_Error - 1 * std_Error): #minValue):
      headingC[idx] = (headingC[idx] + math.pi) % (2 * math.pi)
      change[idx] = [1, sumErrorLoc]
    else:
      headingC[idx] = float('nan')
      change[idx] = [2, sumErrorLoc]

###

boutTimings = dataAPI.listAllBouts(videoName, numWell, numAnimal)

contained_outliers = []

# Iterate through each outlier
for outlier in allOutliers:
  # Check if the outlier falls within any of the bout timing ranges
  for start, end in boutTimings:
    if start <= outlier <= end:
      if intergralOutlierSearch:
        contained_outliers.append([outlier+1, change[outlier]])
      else:
        contained_outliers.append([outlier+1, change[outlier], nbOutliersPerLine[outlier]])
      break

print("Outliers contained within bout timings:", contained_outliers)

###
dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, 'Heading', headingC)
###

# print("number of outliers:", len(allOutliers))
# print(allOutliers)

# plt.plot(data[100])
