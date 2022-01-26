import cv2
import cvui
import numpy as np
import math

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.tailTracking import tailTracking
from zebrazoom.code.trackingFolder.debugTracking import debugTracking

def simpleOptimalValueSearch(PtClosest, contour, unitVector, lenX, lenY):
  
  factor = 0
  dist = 1
  maxDist = 0
  indMax = 0
  testCenter = PtClosest + factor * unitVector
  while (dist > 0) and (factor < 20) and (testCenter[0] >= 0) and (testCenter[1] >= 0) and (testCenter[0] < lenX) and (testCenter[1] < lenY):
    factor = factor + 1
    testCenter = PtClosest + factor * unitVector
    testCenter = testCenter.astype(int)
    dist = cv2.pointPolygonTest(contour, (testCenter[0], testCenter[1]), True)
    if dist > maxDist:
      maxDist = dist
      indMax  = factor
  
  testCenter = PtClosest + indMax * unitVector
  testCenter = testCenter.astype(int)
  
  return testCenter

def reajustCenterOfMassIfNecessary(contour, x, y, lenX, lenY):
  inside = cv2.pointPolygonTest(contour, (x, y), True)
  if inside < 0:
    
    minDist = 100000000000000
    indMin  = 0
    for i in range(0, len(contour)):
      Pt = contour[i][0]
      dist = math.sqrt((Pt[0] - x)**2 + (Pt[1] - y)**2)
      if dist < minDist:
        minDist = dist
        indMin  = i
    PtClosest = contour[indMin][0]
    unitVector = np.array([PtClosest[0] - x, PtClosest[1] - y])
    unitVectorLength = math.sqrt(unitVector[0]**2 + unitVector[1]**2)
    unitVector[0] = unitVector[0] / unitVectorLength
    unitVector[1] = unitVector[1] / unitVectorLength
    if False:
      factor = 5
      testCenter = PtClosest + factor * unitVector
      testCenter = testCenter.astype(int)
      while (cv2.pointPolygonTest(contour, (testCenter[0], testCenter[1]), True) <= 0) and (factor > 1):
        factor = factor - 1
        testCenter = PtClosest + factor * unitVector
    else:
      testCenter = simpleOptimalValueSearch(PtClosest, contour, unitVector, lenX, lenY)
    
    x = testCenter[0]
    y = testCenter[1]
  
  return [x, y]


def fishTailTrackingDifficultBackground(videoPath, wellNumber, wellPositions, hyperparameters, videoName):

  # videoName = "jimmy.mp4"
  showInitialVideo = True
  ROIHalfDiam = 150

  cap = zzVideoReading.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  nbTailPoints = hyperparameters["nbTailPoints"]
  
  trackingHeadTailAllAnimals = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2))
  trackingHeadingAllAnimals  = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1))
  trackingEyesAllAnimals     = 0
  trackingProbabilityOfGoodDetection = 0
  
  fgbg = cv2.createBackgroundSubtractorKNN()
  for i in range(0, min(lastFrame - 1, 500), int(min(lastFrame - 1, 500) / 10)):
    cap.set(1, min(lastFrame - 1, 500) - i)
    ret, frame = cap.read()
    fgmask = fgbg.apply(frame)
  cap.release()
  
  cap = zzVideoReading.VideoCapture(videoPath)
  
  i = firstFrame
  cap.set(1, firstFrame)
  
  while i < lastFrame:
    
    print(i, lastFrame)
    
    ret, frame = cap.read()
    
    if ret:
    
      if i == firstFrame:
        
        WINDOW_NAME = "Click on the center of the head of the animal"
        cvui.init(WINDOW_NAME)
        cv2.moveWindow(WINDOW_NAME, 0,0)
        cvui.imshow(WINDOW_NAME, frame)
        while not(cvui.mouse(cvui.CLICK)):
          cursor = cvui.mouse()
          if cv2.waitKey(20) == 27:
            break
        cv2.destroyAllWindows()
        previousCenterDetectedX = cursor.x
        previousCenterDetectedY = cursor.y
      
      xmin = previousCenterDetectedX - ROIHalfDiam if previousCenterDetectedX - ROIHalfDiam > 0 else 0
      xmax = previousCenterDetectedX + ROIHalfDiam if previousCenterDetectedX + ROIHalfDiam < len(frame[0]) else len(frame[0]) - 1
      ymin = previousCenterDetectedY - ROIHalfDiam if previousCenterDetectedY - ROIHalfDiam > 0 else 0
      ymax = previousCenterDetectedY + ROIHalfDiam if previousCenterDetectedY + ROIHalfDiam < len(frame) else len(frame) - 1
      
      previousCenterDetectedXROICoordinates = previousCenterDetectedX - xmin
      previousCenterDetectedYROICoordinates = previousCenterDetectedY - ymin
      
      if showInitialVideo:
        initialImage = frame.copy()
      
      frame = fgbg.apply(frame)
      
      frame = frame[ymin:ymax, xmin:xmax]
      
      ret, frame = cv2.threshold(frame, 0, 255, cv2.THRESH_BINARY)
      
      im_floodfill = frame.copy()
      h, w = frame.shape[:2]
      mask = np.zeros((h+2, w+2), np.uint8)
      cv2.floodFill(im_floodfill, mask, (0,0), 255);
      im_floodfill_inv = cv2.bitwise_not(im_floodfill)
      frame = frame | im_floodfill_inv
      
      frame = 255 - frame
      
      kernel  = np.ones((3, 3), np.uint8)
      
      countNbOfRightArea = 0
      distanceToPreviousCenterDetected = 100000000000000000000
      countNbTries = 0
      newCenterDetectedX_ROICordinates = previousCenterDetectedXROICoordinates
      newCenterDetectedY_ROICordinates = previousCenterDetectedYROICoordinates
      mostLikelyContour = 0
      while countNbOfRightArea == 0 and countNbTries < 10:
        countNbTries = countNbTries + 1
        frame = cv2.erode(frame, kernel, iterations=1)
        frame[0,:] = 255
        frame[len(frame)-1,:] = 255
        frame[:,0] = 255
        frame[:,len(frame[0])-1] = 255
        contours, hierarchy = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
          contourArea = cv2.contourArea(contour)
          if contourArea > 500 and contourArea < 10000:
            print("contourArea:", contourArea, "; min, max:", hyperparameters["minAreaBody"], hyperparameters["maxAreaBody"])
          if contourArea > hyperparameters["minAreaBody"] and contourArea < hyperparameters["maxAreaBody"]:
            countNbOfRightArea = countNbOfRightArea + 1
            M = cv2.moments(contour)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            [cx, cy] = reajustCenterOfMassIfNecessary(contour, cx, cy, len(frame[0]), len(frame))
            if math.sqrt((previousCenterDetectedXROICoordinates - cx)**2 + (previousCenterDetectedYROICoordinates - cy)**2) < distanceToPreviousCenterDetected:
              newCenterDetectedX_ROICordinates = cx
              newCenterDetectedY_ROICordinates = cy
              mostLikelyContour = contour
        
        print("First: newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates:", newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates)
        
        if type(mostLikelyContour) != int:
          
          cntXmin = 100000000000000
          cntYmin = 100000000000000
          cntXmax = -1
          cntYmax = -1
          
          for point in mostLikelyContour:
            if point[0][0] < cntXmin:
              cntXmin = point[0][0]
            if point[0][1] < cntYmin:
              cntYmin = point[0][1]
            if point[0][0] > cntXmax:
              cntXmax = point[0][0]
            if point[0][1] > cntYmax:
              cntYmax = point[0][1]
        
            cntXmin = cntXmin - 10
            cntYmin = cntYmin - 10
            cntXmax = cntXmax + 10
            cntYmax = cntYmax + 10
          
          if False:
            
            print("This is False")
            # for point in mostLikelyContour:
              # point[0][0] = point[0][0] - cntXmin
              # point[0][1] = point[0][1] - cntYmin
            
            # blank = np.zeros((cntYmax - cntYmin, cntXmax - cntXmin, 3), np.uint8)
            # blank = 255 - blank
            
            # blank = cv2.fillPoly(blank, pts =[mostLikelyContour], color=(0, 0, 0))
            
            # blank = cv2.dilate(blank, kernel, iterations=1)
            # blankIni = blank.copy()
            
            # nbDilationCount = 0
            # blankPreviousIteration = blank
            
            # while cv2.countNonZero(cv2.cvtColor(255 - blank, cv2.COLOR_BGR2GRAY)) != 0 and nbDilationCount < 10:
              # blankPreviousIteration = cv2.cvtColor(blank.copy(), cv2.COLOR_BGR2GRAY)
              # blank = cv2.dilate(blank, kernel, iterations=1)
              # nbDilationCount = nbDilationCount + 1
            
            # contours, hierarchy = cv2.findContours(blankPreviousIteration, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # largestContourArea = 0
            # for contour in contours:
              # contourArea = cv2.contourArea(contour)
              # if contourArea > largestContourArea:
                # largestContourArea = contourArea
                # M = cv2.moments(contour)
                # x = int(M['m10']/M['m00'])
                # y = int(M['m01']/M['m00'])
                # if False:
                  # [newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates] = reajustCenterOfMassIfNecessary(contour, x, y, len(blankPreviousIteration[0]), len(blankPreviousIteration))
                # newCenterDetectedX_ROICordinates = x
                # newCenterDetectedY_ROICordinates = y
          
          else:
              
            cntXmin = 10
            cntYmin = 10
            
            blank = np.zeros((xmax - xmin, ymax - ymin, 3), np.uint8)
            blank = 255 - blank
            
            blank = cv2.fillPoly(blank, pts =[mostLikelyContour], color=(0, 0, 0))
            
            blank = cv2.dilate(blank, kernel, iterations=1)
            blankIni = blank.copy()
            
            nbDilationCount = 0
            blankPreviousIteration = blank
            
            while cv2.countNonZero(cv2.cvtColor(255 - blank, cv2.COLOR_BGR2GRAY)) != 0 and nbDilationCount < 10:
              blankPreviousIteration = cv2.cvtColor(blank.copy(), cv2.COLOR_BGR2GRAY)
              blank = cv2.dilate(blank, kernel, iterations=1)
              nbDilationCount = nbDilationCount + 1
            
            if type(blankPreviousIteration) == np.ndarray and len(blankPreviousIteration) and len(blankPreviousIteration[0]) and type(blankPreviousIteration[0][0]) == np.uint8:
              contours, hierarchy = cv2.findContours(blankPreviousIteration, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
              largestContourArea = 0
              for contour in contours:
                contourArea = cv2.contourArea(contour)
                if contourArea > largestContourArea and contourArea < ((2 * ROIHalfDiam)**2) * 0.8:
                  largestContourArea = contourArea
                  M = cv2.moments(contour)
                  x = int(M['m10']/M['m00'])
                  y = int(M['m01']/M['m00'])
                  # if False:
                    # [newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates] = reajustCenterOfMassIfNecessary(contour, x, y, len(blankPreviousIteration[0]), len(blankPreviousIteration))
                  newCenterDetectedX_ROICordinates = x
                  newCenterDetectedY_ROICordinates = y
      
      print("Second: newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates:", newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates)
      
      trackingHeadTailAllAnimals[0, i-firstFrame][0][0] = newCenterDetectedX_ROICordinates
      trackingHeadTailAllAnimals[0, i-firstFrame][0][1] = newCenterDetectedY_ROICordinates
      
      if hyperparameters["trackTail"] == 1:
        if type(blankIni) == np.ndarray and len(blankIni) and len(blankIni[0]):
          if type(blankIni[0][0]) != np.uint8:
            blankIni = cv2.cvtColor(blankIni, cv2.COLOR_BGR2GRAY)
          for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
            [trackingHeadTailAllAnimals, trackingHeadingAllAnimals] = tailTracking(animalId, i, firstFrame, videoPath, blankIni, hyperparameters, blankIni, nbTailPoints, blankIni, 0, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, 0, 0, 0, blankIni, 0, wellNumber)
        else:
          print("problem")
      
      for j in range(0, len(trackingHeadTailAllAnimals[0, i-firstFrame])):
        trackingHeadTailAllAnimals[0, i-firstFrame][j][0] += xmin + cntXmin - 10
        trackingHeadTailAllAnimals[0, i-firstFrame][j][1] += ymin + cntYmin - 10
      
      debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, initialImage, hyperparameters)
      # if showInitialVideo:
        # initialImage = cv2.circle(initialImage, (newCenterDetectedX_ROICordinates + xmin + cntXmin - 10, newCenterDetectedY_ROICordinates + ymin + cntYmin - 10), 3, (255, 0, 0), 2)
        # cv2.imshow("frame", initialImage)
        # cv2.waitKey(0)
      # else:
        # frame = cv2.circle(frame, (newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates), 3, (255, 0, 0), 2)
        # cv2.imshow("frame", frame)
        # cv2.waitKey(0)
      
      previousCenterDetectedX = newCenterDetectedX_ROICordinates + xmin + cntXmin - 10
      previousCenterDetectedY = newCenterDetectedY_ROICordinates + ymin + cntYmin - 10
    
    i = i + 1

  cv2.destroyAllWindows()
  
  return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals]
