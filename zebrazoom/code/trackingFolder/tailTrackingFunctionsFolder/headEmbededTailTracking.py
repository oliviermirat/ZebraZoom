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
from scipy.interpolate import interp1d
from scipy.interpolate import splprep, splev


def smoothTail(points, nbTailPoints, smoothingFactor):
  
  points3 = [np.array(points[0]), np.array(points[1])]
  
  y = points[0]
  x = linspace(0, 1, len(y))
    
  if len(x) > 3:
    interpolated_points = {}
    
    try:
      if smoothingFactor != -1:
        tck, u = splprep(points3, s=smoothingFactor)
      else:
        tck, u = splprep(points3)
      u2 = [i/(nbTailPoints-1) for i in range(0, nbTailPoints)]
      interpolated_points = splev(u2, tck)
      newX = interpolated_points[0]
      newY = interpolated_points[1]
    except:
      newX = points[0]
      newY = points[1]
    
  else:
    newX = points[0]
    newY = points[1]
  
  return [newX, newY]


def interpolateTail(points, nbTailPoints):

  y = points[0]
  x = linspace(0, 1, len(y))
    
  if len(x) > 3:
    
    points2 = []
    for i in range(0, len(points[0])-1):
      if not((points[0][i] == points[0][i+1]) and (points[1][i] == points[1][i+1])):
        points2.append([points[0][i], points[1][i]])

    i = len(points[0]) - 1
    if not((points[0][i-1] == points[0][i]) and (points[1][i-1] == points[1][i])):
      points2.append([points[0][i], points[1][i]])
        
    points = np.array(points2).T
    
    # Define some points:
    points = np.array([points[0], points[1]]).T  # a (nbre_points x nbre_dim) array

    # Linear length along the line:
    distance = np.cumsum( np.sqrt(np.sum( np.diff(points, axis=0)**2, axis=1 )) )
    distance = np.insert(distance, 0, 0)/distance[-1]

    # Interpolation for different methods:
    interpolation_method = 'quadratic'    # 'slinear', 'quadratic', 'cubic'
    alpha = np.linspace(0, 1, nbTailPoints)

    interpolated_points = {}
    
    interpolator =  interp1d(distance, points, kind=interpolation_method, axis=0)
    interpolated_points = interpolator(alpha)
    
    interpolated_points = interpolated_points.T
    
    newX = interpolated_points[0]
    newY = interpolated_points[1]
    
  else:
    
    newX = points[0]
    newY = points[1]
  
  return [newX, newY]


def appendPoint(x, y, points):
  curPoint = np.zeros((2, 1))
  curPoint[0] = x;
  curPoint[1] = y;
  points = np.append(points, curPoint, axis=1)
  return points

def findNextPoints(depth,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,debug, hyperparameters, dontChooseThisPoint = [], maxRadiusForDontChoosePoint = 0):
  
  lenX = len(frame[0]) - 1
  lenY = len(frame) - 1

  thetaDiffAccept = 1
  
  if depth < hyperparameters["initialTailPortionMaxSegmentDiffAngleCutOffPos"] * maxDepth:
    thetaDiffAccept = hyperparameters["initialTailPortionMaxSegmentDiffAngleValue"]
  
  if depth > 0.85*maxDepth:
    thetaDiffAccept = 0.6
  
  if hyperparameters["headEmbededMaxAngleBetweenSubsequentSegments"]:
    thetaDiffAccept = hyperparameters["headEmbededMaxAngleBetweenSubsequentSegments"]
  
  pixTotMax = 1000000
  maxTheta  = angle

  l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]
  
  # if debug:
    # print("debug")
  
  for step in steps:
    
    if (step < maxDepth - depth) or (step == steps[0]):
    
      for theta in l:
        
        xNew = assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
        yNew = assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
        pixTot = frame[yNew][xNew]
        
        # if debug:
          # print([theta,pixTot])
        
        # Keeps that theta angle as maximum if appropriate
        if (pixTot < pixTotMax):
          if (len(dontChooseThisPoint) == 0):
            pixTotMax = pixTot
            maxTheta = theta
            xTot = xNew
            yTot = yNew
          else:
            dist = 1000000000000000000
            for num in range(0, len(dontChooseThisPoint[0])):
              dist = min(dist, math.sqrt((xNew - dontChooseThisPoint[0, num])**2 + (yNew - dontChooseThisPoint[1, num])**2))
            if (not(dist <= maxRadiusForDontChoosePoint)):
              pixTotMax = pixTot
              maxTheta = theta
              xTot = xNew
              yTot = yNew
  
  w = 4
  ym = yTot - w
  yM = yTot + w
  xm = xTot - w
  xM = xTot + w
  if ym < 0:
    ym = 0
  if xm < 0:
    xm = 0
  if yM > len(initialImage):
    yM = len(initialImage)
  if xM > len(initialImage[0]):
    xM = len(initialImage[0])
  
  pixSur = np.min(frame[ym:yM, xm:xM]) #initialImage[ym:yM, xm:xM])
  # if debug:
    # print("depth:", depth, " ; maxDepth:", maxDepth, " ; pixSur:", pixSur)
  
  # if depth > 0.95*maxDepth:
    # pixTot = frame[y][x]
    # if (pixTot < pixTotMax):
      # pixTotMax = pixTot
      # maxTheta = theta
      # xTot = x
      # yTot = y
      # depth = maxDepth + 10
  
  # if debug:
    # print(["max:",maxTheta,pixTotMax])
  
  # Calculates distance between new and old point
  distSubsquentPoints = math.sqrt((xTot - x)**2 + (yTot - y)**2)
  
  pixSurMax = hyperparameters["headEmbededParamTailDescentPixThreshStop"]
  # pixSurMax = 220 #150 #245 #150
  if depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
    points = appendPoint(xTot, yTot, points)
  else:
    vectX = xTot - x
    vectY = yTot - y
    xTot  = int(x + (maxDepth / (depth + distSubsquentPoints)) * vectX)
    yTot  = int(y + (maxDepth / (depth + distSubsquentPoints)) * vectY)
    points = appendPoint(xTot, yTot, points)
  if debug:
    import zebrazoom.code.util as util

    cv2.circle(frame, (xTot, yTot), 3, (255,0,0),   -1)
    util.showFrame(frame, title='HeadEmbeddedTailTracking')
    
  newTheta = calculateAngle(x,y,xTot,yTot)
  if distSubsquentPoints > 0 and depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
    (points,nop) = findNextPoints(depth+distSubsquentPoints,xTot,yTot,frame,points,newTheta,maxDepth,steps,nbList,initialImage,debug, hyperparameters)
  
  if depth == 0:
    lenPoints = len(points[0]) - 1
    if points[0, lenPoints-1] == points[0, lenPoints] and points[1, lenPoints-1] == points[1, lenPoints]:
      points = points[:, :len(points[0])-1]
  
  return (points,newTheta)


def weirdTrackingPoints(points, headPosition, tailTip):

  newTrackedTipX = points[0, len(points[0]) - 1]
  newTrackedTipY = points[1, len(points[0]) - 1]
  
  distInitialHeadToNewTrackedTip = math.sqrt((headPosition[0] - newTrackedTipX)**2 + (headPosition[1] - newTrackedTipY)**2)
  distInitialTipToNewTrackTip    = math.sqrt((tailTip[0] - newTrackedTipX)**2 + (tailTip[1] - newTrackedTipY)**2)
  
  initialTailLength = math.sqrt((headPosition[0] - tailTip[0])**2 + (headPosition[1] - tailTip[1])**2)
  
  if (initialTailLength * 0.7 < distInitialHeadToNewTrackedTip) and (distInitialHeadToNewTrackedTip <initialTailLength * 1.3 ) and (distInitialTipToNewTrackTip < initialTailLength):
    return False
  else:
    return True
  

def retrackIfWeirdInitialTracking(points, headPosition, tailTip, hyperparameters, x, y, frame, angle, maxDepth, nbList, initialImage, i):
  
  steps = hyperparameters["step"]
  
  if weirdTrackingPoints(points, headPosition, tailTip):
    dontTakeThesePoints       = points.copy()
    dontTakeThesePointsAdding = points.copy()
    pointNumTest   = 0
    steps3 = [indStep for indStep in range(steps[0], steps[len(steps)-1])]
    # First Attempt: for each of the previously tracked points, prevent new tracking from choosing that previously tracked point + steps change
    while (weirdTrackingPoints(points, headPosition, tailTip)) and (pointNumTest < len(dontTakeThesePoints[0])):
      points = np.zeros((2, 0))
      (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,maxDepth,steps3,nbList,initialImage,hyperparameters["debugHeadEmbededFindNextPoints"], hyperparameters, np.transpose(np.array([dontTakeThesePoints[:,pointNumTest]])))
      dontTakeThesePointsAdding = np.concatenate((dontTakeThesePointsAdding, points), axis=1)
      dontTakeThesePointsAdding = np.unique(dontTakeThesePointsAdding, axis=1)
      points = np.insert(points, 0, headPosition, axis=1)
      pointNumTest = pointNumTest + 1
    
    if (pointNumTest == len(dontTakeThesePoints[0])) and (weirdTrackingPoints(points, headPosition, tailTip)):
      pointNumTest   = 0
      # Second Attempt: for each of the previously tracked points, prevent new tracking from choosing any point in a 2 pixel radius of that previously tracked point + steps change
      while (weirdTrackingPoints(points, headPosition, tailTip)) and (pointNumTest < len(dontTakeThesePoints[0])):
        points = np.zeros((2, 0))
        (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,maxDepth,steps3,nbList,initialImage,hyperparameters["debugHeadEmbededFindNextPoints"], hyperparameters, np.transpose(np.array([dontTakeThesePoints[:,pointNumTest]])), 2)
        dontTakeThesePointsAdding = np.concatenate((dontTakeThesePointsAdding, points), axis=1)
        dontTakeThesePointsAdding = np.unique(dontTakeThesePointsAdding, axis=1)
        points = np.insert(points, 0, headPosition, axis=1)
        pointNumTest = pointNumTest + 1
    
    if (pointNumTest == len(dontTakeThesePoints[0])) and (weirdTrackingPoints(points, headPosition, tailTip)):
      points = np.zeros((2, 0))
      # Third attempt: prevents new tracking from choosing any of the initially tracked points as well as all the points tracked in the second and third attempt + step change
      (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,maxDepth,steps3,nbList,initialImage,hyperparameters["debugHeadEmbededFindNextPoints"], hyperparameters, dontTakeThesePointsAdding, 0)
      points = np.insert(points, 0, headPosition, axis=1) 

    if (pointNumTest == len(dontTakeThesePoints[0])) and (weirdTrackingPoints(points, headPosition, tailTip)):
      points = np.zeros((2, 0))
      # Third attempt: prevents new tracking from choosing any of the initially tracked points as well as all the points tracked in the second and third attempt + extended step change
      steps2 = [indStep for indStep in range(max(0, steps[0]-1), steps[len(steps)-1]+4)]
      (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,maxDepth,steps2,nbList,initialImage,hyperparameters["debugHeadEmbededFindNextPoints"], hyperparameters, dontTakeThesePointsAdding, 0)
      points = np.insert(points, 0, headPosition, axis=1)       
    
    if (pointNumTest == len(dontTakeThesePoints[0])) and (weirdTrackingPoints(points, headPosition, tailTip)):
      print("PROBLEM for frame", i, "despite applying correction procedure")
    else:
      print("Ok! Problem solved for frame", i)
  
  return points


def headEmbededTailTracking(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,heading,maxDepth,tailTip):
  steps   = hyperparameters["step"]
  nbList  = 10 if hyperparameters["nbList"] == -1 else hyperparameters["nbList"]
  
  x = headPosition[0]
  y = headPosition[1]
  
  initialImage = frame.copy()
  
  gaussian_blur = hyperparameters["headEmbededParamGaussianBlur"]
  
  frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
  # angle = hyperparameters["headEmbededParamInitialAngle"]
  angle = calculateAngle(x, y, tailTip[0], tailTip[1])
  
  points = np.zeros((2, 0))
  
  (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,hyperparameters["debugHeadEmbededFindNextPoints"], hyperparameters)
  points = np.insert(points, 0, headPosition, axis=1)
  
  # Anomalie detection here
  headEmbededRetrackIfWeirdInitialTracking = hyperparameters["headEmbededRetrackIfWeirdInitialTracking"]
  if headEmbededRetrackIfWeirdInitialTracking:
    points = retrackIfWeirdInitialTracking(points, headPosition, tailTip, hyperparameters, x, y, frame, angle, maxDepth, nbList, initialImage, i)
  
  if len(points[0]) > 3:
    if hyperparameters["smoothTailHeadEmbeded"]:
      for smoothTailIteration in range(0, hyperparameters["smoothTailHeadEmbededNbOfIterations"]):
        points = smoothTail(points, nbTailPoints, hyperparameters["smoothTailHeadEmbeded"])
    else:
      if not(hyperparameters["adjustHeadEmbededTracking"]):
        points   = interpolateTail(points, nbTailPoints)
      else:
        nDist    = len(points[0]) - 1
        stepDist = 10 / nDist
        tab      = [int((i/9)*nDist) for i in range(0,10)]
        points   = [[points[0][i] for i in tab], [points[1][i] for i in tab]]
  
  output = np.zeros((1, len(points[0]), 2))

  for idx, x in enumerate(points[0]):
    output[0][idx][0] = x
    output[0][idx][1] = points[1][idx]

  return output


def headEmbededTailTrackFindMaxDepth(headPosition,nbTailPoints,i,x,y,thresh1,frame,hyperparameters,oppHeading,tailTip):
  
  if True:
    return math.sqrt((headPosition[0] - tailTip[0])**2 + (headPosition[1] - tailTip[1])**2)
  
  headEmbededParamTailDescentPixThreshStopInit = hyperparameters["headEmbededParamTailDescentPixThreshStop"]
  hyperparameters["headEmbededParamTailDescentPixThreshStop"] = 256
  
  x = headPosition[0]
  y = headPosition[1]

  steps   = hyperparameters["step"]
  nbList  = 10
  
  initialImage = frame.copy()
  
  gaussian_blur = hyperparameters["headEmbededParamGaussianBlur"]
  
  frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
  
  angle = calculateAngle(x, y, tailTip[0], tailTip[1])
  
  points = np.zeros((2, 0))
  
  (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"],steps,nbList,initialImage, hyperparameters["debugHeadEmbededFindNextPoints"], hyperparameters)
  
  distToTip        = np.full((200),10000)
  distToBase       = np.full((200),10000)
  curTailLengthTab = np.full((200),10000)
  curTailLength  = 0
  
  k = 0
  distToTip[k]        = abs(math.sqrt((points[0,k]-tailTip[0])**2 + (points[1,k]-tailTip[1])**2))
  distToBase[k]       = abs(math.sqrt((points[0,k] - x)**2 + (points[1,k] - y)**2))
  curTailLength       = abs(math.sqrt((points[0,k] - x)**2 + (points[1,k] - y)**2))
  curTailLengthTab[k] = curTailLength
  
  k = 1
  distFromHeadToTip = abs(math.sqrt((x-tailTip[0])**2 + (y-tailTip[1])**2))
  while (curTailLength < 1.5*distFromHeadToTip) and (k < len(points[0])-1):
    curTailLength = curTailLength + abs(math.sqrt((points[0,k]-points[0,k-1])**2 + (points[1,k]-points[1,k-1])**2))
    distToTip[k]  = abs(math.sqrt((points[0,k]-tailTip[0])**2 + (points[1,k]-tailTip[1])**2))
    distToBase[k] = abs(math.sqrt((points[0,k] - x)**2 + (points[1,k] - y)**2))
    curTailLengthTab[k] = curTailLength
    k = k + 1
  
  minDistToTip    = 1000000
  indMinDistToTip = 0
  for idx, dist in enumerate(distToTip):
    if dist < minDistToTip:
      minDistToTip = dist
      indMinDistToTip = idx
  
  hyperparameters["headEmbededParamTailDescentPixThreshStop"] = headEmbededParamTailDescentPixThreshStopInit
  
  pathFactor = curTailLengthTab[indMinDistToTip] / distToBase[indMinDistToTip]
  
  return (math.sqrt((x - tailTip[0])**2 + (y - tailTip[1])**2)* pathFactor)


def adjustHeadEmbededHyperparameters(hyperparameters, frame, headPosition, tailTip):
  
  dist = math.sqrt((headPosition[0] - tailTip[0])**2 + (headPosition[1] - tailTip[1])**2)
  factor = dist / 220
  
  if hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]:
    hyperparameters["headEmbededRemoveBack"] = 1
    hyperparameters["minPixelDiffForBackExtract"] = hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] # 7
    # if hyperparameters["invertBlackWhiteOnImages"] == 0:
    hyperparameters["extractBackWhiteBackground"] = 0
    # else:
      # hyperparameters["extractBackWhiteBackground"] = 1
  
  if hyperparameters["headEmbededAutoSet_ExtendedDescentSearchOption"]:
    initialStepsTab = [10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50]
  else:
    initialStepsTab = [10, 13, 15]
  hyperparameters["step"] = [int(val*factor) for val in initialStepsTab]
  hyperparameters["step"] = list(dict.fromkeys(hyperparameters["step"])) # removes duplicate values
  if len(hyperparameters["step"]) == 0:
    hyperparameters["step"] = [2, 4]
    
  if hyperparameters["overwriteFirstStepValue"] or hyperparameters["overwriteLastStepValue"]:
    hyperparameters["overwriteFirstStepValue"] = int(hyperparameters["overwriteFirstStepValue"])
    hyperparameters["overwriteLastStepValue"]  = int(hyperparameters["overwriteLastStepValue"])
    if hyperparameters["overwriteLastStepValue"] <= hyperparameters["overwriteFirstStepValue"]:
      hyperparameters["overwriteLastStepValue"] = hyperparameters["overwriteFirstStepValue"] + 1
    hyperparameters["overwriteNbOfStepValues"] = hyperparameters["overwriteLastStepValue"] - hyperparameters["overwriteFirstStepValue"] + 1
    step = [hyperparameters["overwriteFirstStepValue"] + stepVal for stepVal in range(0, hyperparameters["overwriteNbOfStepValues"])]
    hyperparameters["step"] = step
  
  hyperparameters["headEmbededParamGaussianBlur"] = int(13 * factor)
  
  if hyperparameters["overwriteHeadEmbededParamGaussianBlur"]:
    hyperparameters["headEmbededParamGaussianBlur"] = int(hyperparameters["overwriteHeadEmbededParamGaussianBlur"])
  
  if hyperparameters["headEmbededParamGaussianBlur"] % 2 == 0:
    hyperparameters["headEmbededParamGaussianBlur"] = hyperparameters["headEmbededParamGaussianBlur"] + 1
  
  hyperparameters["addBlackCircleOfHalfDiamOnHeadForBoutDetect"] = int(70 * factor)
  
  hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"] = int(300*factor)
  
  hyperparameters["trackingPointSizeDisplay"] = int(5*factor) if int(5*factor) > 0 else 1 # CAN DO BETTER HERE !!!
  
  tailTipSurroundingDiameter = int(15 * factor)
  x = tailTip[0]
  y = tailTip[1]
  videoWidth  = hyperparameters["videoWidth"]
  videoHeight = hyperparameters["videoHeight"]
  if y-tailTipSurroundingDiameter < 0:
    ymin = 0
  else:
    ymin = y-tailTipSurroundingDiameter
  if y+tailTipSurroundingDiameter > videoHeight:
    ymax = videoHeight - 1
  else:
    ymax = y+tailTipSurroundingDiameter
  if x-tailTipSurroundingDiameter < 0:
    xmin = 0
  else:
    xmin = x-tailTipSurroundingDiameter
  if x+tailTipSurroundingDiameter > videoWidth:
    xmax = videoWidth - 1
  else:
    xmax = x+tailTipSurroundingDiameter
  hyperparameters["headEmbededParamTailDescentPixThreshStop"] = int(np.mean(frame[int(ymin):int(ymax), int(xmin):int(xmax)]))
  
  if hyperparameters["headEmbededParamTailDescentPixThreshStopOverwrite"] != -1:
    hyperparameters["headEmbededParamTailDescentPixThreshStop"] = hyperparameters["headEmbededParamTailDescentPixThreshStopOverwrite"]
  
  
  if False:
    print("headEmbededParamTailDescentPixThreshStop:", hyperparameters["headEmbededParamTailDescentPixThreshStop"])
    print("dist:", dist)
    print("step:", hyperparameters["step"])
    print("headEmbededParamGaussianBlur:", hyperparameters["headEmbededParamGaussianBlur"])
    print("trackingPointSizeDisplay:", hyperparameters["trackingPointSizeDisplay"])

  return hyperparameters
