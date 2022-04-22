import numpy as np
import cv2
import math
import zebrazoom.code.util as util
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.calculateHeading import computeHeading
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas

def eyeTracking(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals):
  
  headCenterToMidEyesPointDistance   = hyperparameters["headCenterToMidEyesPointDistance"]
  eyeBinaryThreshold                 = hyperparameters["eyeBinaryThreshold"]
  midEyesPointToEyeCenterMaxDistance = hyperparameters["midEyesPointToEyeCenterMaxDistance"]
  eyeHeadingSearchAreaHalfDiameter   = hyperparameters["eyeHeadingSearchAreaHalfDiameter"]
  headingLineValidationPlotLength    = hyperparameters["headingLineValidationPlotLength"]
  debugEyeTracking                   = hyperparameters["debugEyeTracking"]
  debugEyeTrackingAdvanced           = hyperparameters["debugEyeTrackingAdvanced"]
  
  # Retrieving the X, Y coordinates of the center of the head of the fish and calculating the "mid eyes" point
  x = trackingHeadTailAllAnimals[animalId, i-firstFrame][0][0]
  y = trackingHeadTailAllAnimals[animalId, i-firstFrame][0][1]
  midEyesPointX = int(x+headCenterToMidEyesPointDistance*math.cos(trackingHeadingAllAnimals[animalId, i-firstFrame]))
  midEyesPointY = int(y+headCenterToMidEyesPointDistance*math.sin(trackingHeadingAllAnimals[animalId, i-firstFrame]))
  
  # Finding the connected components associated with each of the two eyes 
  ret, threshEye = cv2.threshold(frame, eyeBinaryThreshold, 255, cv2.THRESH_BINARY)
  threshEye[0,:] = 255
  threshEye[len(threshEye)-1,:] = 255
  threshEye[:,0] = 255
  threshEye[:,len(threshEye[0])-1] = 255
  # Adding a white circle on the swim bladder
  whiteCircleDiameter = int(1.2 * headCenterToMidEyesPointDistance)
  whiteCircleX = int(x-whiteCircleDiameter*math.cos(trackingHeadingAllAnimals[animalId, i-firstFrame]))
  whiteCircleY = int(y-whiteCircleDiameter*math.sin(trackingHeadingAllAnimals[animalId, i-firstFrame]))  
  cv2.circle(threshEye, (whiteCircleX, whiteCircleY), whiteCircleDiameter, (255, 255, 255), -1)
  maxArea1    = 0 # Biggest of the two contours
  maxContour1 = 0
  maxArea2    = 0 # Smallest of the two contours
  maxContour2 = 0
  contours, hierarchy = cv2.findContours(threshEye, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  for contour in contours:
    area = cv2.contourArea(contour)
    M = cv2.moments(contour)
    if M['m00']:
      cx = int(M['m10']/M['m00'])
      cy = int(M['m01']/M['m00'])
    else:
      cx = 0
      cy = 0
    if area < (len(frame)*len(frame[0]))/2 and math.sqrt((cx - midEyesPointX)**2 + (cy - midEyesPointY)**2) < midEyesPointToEyeCenterMaxDistance:
      if (area > maxArea1):
        maxArea2    = maxArea1
        maxContour2 = maxContour1
        maxArea1    = area
        maxContour1 = contour
      else:
        if (area > maxArea2):
          maxArea2    = area
          maxContour2 = contour
  if debugEyeTrackingAdvanced:
    util.showFrame(threshEye, title='Frame')
  # Finding, in the image without the white circle, the contours corresponding to the contours previously found in the image with the white circle
  # This to make sure that we get the blobs that "really" correspond to the eyes in the unlikely event where the white circle would have overlapped with the eyes
  M = cv2.moments(maxContour1)
  if M['m00']:
    eye1X = int(M['m10']/M['m00'])
    eye1Y = int(M['m01']/M['m00'])
  else:
    eye1X = 0
    eye1Y = 0
  M = cv2.moments(maxContour2)
  if M['m00']:
    eye2X = int(M['m10']/M['m00'])
    eye2Y = int(M['m01']/M['m00'])
  else:
    eye2X = 0
    eye2Y = 0
  maxContour1b = maxContour1
  maxContour2b = maxContour2
  ret, threshEye2 = cv2.threshold(frame, eyeBinaryThreshold, 255, cv2.THRESH_BINARY)
  threshEye2[0,:] = 255
  threshEye2[len(threshEye2)-1,:] = 255
  threshEye2[:,0] = 255
  threshEye2[:,len(threshEye2[0])-1] = 255
  contours, hierarchy = cv2.findContours(threshEye2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  for contour in contours:
    dist1 = cv2.pointPolygonTest(contour, (eye1X, eye1Y), True)
    dist2 = cv2.pointPolygonTest(contour, (eye2X, eye2Y), True)
    if dist1 >= 0:
      maxContour1b = contour
    if dist2 >= 0:
      maxContour2b = contour
  # Finding the left and the right eyes
  M = cv2.moments(maxContour1b)
  if M['m00']:
    eye1X = int(M['m10']/M['m00'])
    eye1Y = int(M['m01']/M['m00'])
  else:
    eye1X = 0
    eye1Y = 0
  M = cv2.moments(maxContour2b)
  if M['m00']:
    eye2X = int(M['m10']/M['m00'])
    eye2Y = int(M['m01']/M['m00'])
  else:
    eye2X = 0
    eye2Y = 0  
  distBetweenTheTwoEyes = math.sqrt((eye1X - eye2X)**2 + (eye1Y - eye2Y)**2)
  estimatedLeftEyeX = int(midEyesPointX + (distBetweenTheTwoEyes/2) * math.cos(trackingHeadingAllAnimals[animalId, i-firstFrame] - (math.pi/2)))
  estimatedLeftEyeY = int(midEyesPointY + (distBetweenTheTwoEyes/2) * math.sin(trackingHeadingAllAnimals[animalId, i-firstFrame] - (math.pi/2)))
  contour1ToEstimatedLeftEyeYdistance = math.sqrt((estimatedLeftEyeX - eye1X)**2 + (estimatedLeftEyeY - eye1Y)**2)
  contour2ToEstimatedLeftEyeYdistance = math.sqrt((estimatedLeftEyeX - eye2X)**2 + (estimatedLeftEyeY - eye2Y)**2)
  if contour1ToEstimatedLeftEyeYdistance < contour2ToEstimatedLeftEyeYdistance:
    contourLeft  = maxContour1b
    contourRight = maxContour2b
  else:
    contourLeft  = maxContour2b
    contourRight = maxContour1b
  # Finding the (X, Y) coordinates and the angle of each of the two eyes
  eyeX     = [0, 0]
  eyeY     = [0, 0]
  eyeAngle = [0, 0]
  eyeArea  = [0, 0]
  for idx, contour in enumerate([contourLeft, contourRight]):
    eyeArea[idx] = cv2.contourArea(contour)
    M = cv2.moments(contour)
    if M['m00']:
      eyeX[idx] = int(M['m10']/M['m00'])
      eyeY[idx] = int(M['m01']/M['m00'])
    if type(contour) != int and len(contour) >= 3:
      if len(contour) >= 5:
        ellipse = cv2.fitEllipse(contour)
        angle1 = ellipse[2] * (math.pi / 180) + (math.pi / 2)
      else:
        print("problem with eye angle here, not enough points in the contour to use fitEllipse")
        threshEye1 = np.zeros((len(threshEye), len(threshEye[0])))
        threshEye1[:, :] = 0
        cv2.fillPoly(threshEye1, pts =[contour], color=(255))
        if debugEyeTrackingAdvanced:
          util.showFrame(threshEye1, title='Frame')
        if False:
          angle1 = computeHeading(threshEye1, eyeX[idx], eyeY[idx], eyeHeadingSearchAreaHalfDiameter, hyperparameters)
        else:
          minWhitePixel = 10000000000000000000000
          bestAngle     = 0
          nTries        = 200
          for j in range(0, nTries):
            angleOption = j * (math.pi / nTries)
            startPoint = (int(eyeX[idx] - 100000 * math.cos(angleOption)), int(eyeY[idx] - 100000 * math.sin(angleOption)))
            endPoint   = (int(eyeX[idx] + 100000 * math.cos(angleOption)), int(eyeY[idx] + 100000 * math.sin(angleOption)))
            testImage  = threshEye1.copy()
            testImage  = cv2.line(testImage, startPoint, endPoint, (0), 4)
            nbWhitePixels = cv2.countNonZero(testImage)
            if nbWhitePixels < minWhitePixel:
              minWhitePixel = nbWhitePixels
              bestAngle     = angleOption
            if False:
              firstBestAngle = bestAngle
              for j in range(0, nTries):
                angleOption = firstBestAngle - (math.pi / 5) + j * ((2 * (math.pi / 5)) / nTries)
                startPoint = (int(eyeX[idx] - 100000 * math.cos(angleOption)), int(eyeY[idx] - 100000 * math.sin(angleOption)))
                endPoint   = (int(eyeX[idx] + 100000 * math.cos(angleOption)), int(eyeY[idx] + 100000 * math.sin(angleOption)))
                testImage  = threshEye1.copy()
                testImage  = cv2.line(testImage, startPoint, endPoint, (0), 4)
                nbWhitePixels = cv2.countNonZero(testImage)
                if nbWhitePixels < minWhitePixel:
                  minWhitePixel = nbWhitePixels
                  bestAngle     = angleOption
          angle1 = bestAngle
      
      headingApproximate = trackingHeadingAllAnimals[animalId, i-firstFrame] % (2*math.pi)
      headingPreciseOpt1 = angle1
      headingPreciseOpt2 = (angle1 + math.pi) % (2*math.pi)
      diffAngle1 = distBetweenThetas(headingApproximate, headingPreciseOpt1)
      diffAngle2 = distBetweenThetas(headingApproximate, headingPreciseOpt2)
      if (diffAngle1 < diffAngle2):
        eyeAngle[idx] = headingPreciseOpt1
      else:
        eyeAngle[idx] = headingPreciseOpt2
    else:
      eyeAngle[idx] = 0
  # Debugging Plot
  if debugEyeTracking:
    colorFrame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    cv2.line(colorFrame, (int(x),int(y)), (int(x+2*headingLineValidationPlotLength*math.cos(trackingHeadingAllAnimals[animalId, i-firstFrame])), int(y+2*headingLineValidationPlotLength*math.sin(trackingHeadingAllAnimals[animalId, i-firstFrame]))), (255,0,0), 1)
    cv2.circle(colorFrame, (midEyesPointX, midEyesPointY), 2, (255,0,255), 1)
    cv2.circle(colorFrame, (eyeX[0], eyeY[0]), 2, (0,255,255), 1)
    cv2.line(colorFrame, (eyeX[0], eyeY[0]), (int(eyeX[0]+headingLineValidationPlotLength*math.cos(eyeAngle[0])), int(eyeY[0]+headingLineValidationPlotLength*math.sin(eyeAngle[0]))), (255,0,255), 1)
    cv2.line(colorFrame, (eyeX[1], eyeY[1]), (int(eyeX[1]+headingLineValidationPlotLength*math.cos(eyeAngle[1])), int(eyeY[1]+headingLineValidationPlotLength*math.sin(eyeAngle[1]))), (255,0,255), 1)
    cv2.circle(colorFrame, (eyeX[1], eyeY[1]), 2, (0,255,255), 1)
    util.showFrame(colorFrame, title='Eye Tracking debugging')
  
  # Storing the (X, Y) coordinates and angles
  trackingEyesAllAnimals[animalId, i-firstFrame, 0] = eyeX[0]
  trackingEyesAllAnimals[animalId, i-firstFrame, 1] = eyeY[0]
  trackingEyesAllAnimals[animalId, i-firstFrame, 2] = eyeAngle[0]
  trackingEyesAllAnimals[animalId, i-firstFrame, 3] = eyeArea[0]
  trackingEyesAllAnimals[animalId, i-firstFrame, 4] = eyeX[1]
  trackingEyesAllAnimals[animalId, i-firstFrame, 5] = eyeY[1]
  trackingEyesAllAnimals[animalId, i-firstFrame, 6] = eyeAngle[1]
  trackingEyesAllAnimals[animalId, i-firstFrame, 7] = eyeArea[1]
  
  return trackingEyesAllAnimals
