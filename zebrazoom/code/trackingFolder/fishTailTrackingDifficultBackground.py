import cv2
import numpy as np
import math
import pickle
import os

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util
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
  
def fillWhiteHoles(frame):
  
  frameBeforeWhiteFill = frame.copy()
  im_floodfill = frame.copy()
  h, w = frame.shape[:2]
  mask = np.zeros((h+2, w+2), np.uint8)
  cv2.floodFill(im_floodfill, mask, (0,0), 255);
  im_floodfill_inv = cv2.bitwise_not(im_floodfill)
  frame = frame | im_floodfill_inv
  
  if cv2.countNonZero(frame) > (len(frame) * len(frame[0])) * 0.95:
    frame = frameBeforeWhiteFill
    print("BACK TO IMAGE BEFORE WHITE FILL")
  
  return frame
  
def erodeThenAddWhiteBorders(frame, kernel):
  frame = cv2.erode(frame, kernel, iterations=1)
  frame[0,:] = 255
  frame[len(frame)-1,:] = 255
  frame[:,0] = 255
  frame[:,len(frame[0])-1] = 255
  return frame

def erodeThenDilateThenAddWhiteBorders(frame, kernel, nbOfIterations):
  frame = cv2.erode(frame, kernel, iterations=nbOfIterations)
  frame = cv2.dilate(frame, kernel, iterations=nbOfIterations)
  frame[0,:] = 255
  frame[len(frame)-1,:] = 255
  frame[:,0] = 255
  frame[:,len(frame[0])-1] = 255
  return frame

def addWhiteBorders(frame):
  frame[0,:] = 255
  frame[len(frame)-1,:] = 255
  frame[:,0] = 255
  frame[:,len(frame[0])-1] = 255
  return frame

def fishTailTrackingDifficultBackground(videoPath, wellNumber, wellPositions, hyperparameters, videoName):
  
  chooseValueForAnimalBodyArea = -1 #600 # -1
  showInitialVideo = True # This is not used anymore, should be removed soon
  iterativelyErodeEachImage = False
  showFramesForDebugging = hyperparameters["debugTracking"]
  dist2Threshold = 400
  historyLength  = 1000
  reduceImageResolutionPercentage = hyperparameters["reduceImageResolutionPercentage"]
  
  pathToVideo = os.path.split(videoPath)[0]
  
  kernel  = np.ones((3, 3), np.uint8)
  ROIHalfDiam = -1
  
  class CustomError(Exception):
    pass

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
  
  fgbg = cv2.createBackgroundSubtractorKNN(dist2Threshold = dist2Threshold, history = historyLength)
  
  if os.path.exists(os.path.join(pathToVideo, videoName + '_BackgroundKNN_' + str(historyLength) + '.pkl')):
    print("Background already pre-calculated")
    with open(os.path.join(pathToVideo, videoName + '_BackgroundKNN_' + str(historyLength) + '.pkl'), 'rb') as handle:
      listOfFramesToSave = pickle.load(handle)
    for i in range(0, len(listOfFramesToSave)):
      print("calculating background, currently at frame:", i)
      frame = listOfFramesToSave[i]
      fgmask = fgbg.apply(frame)
  else:
    print("Background calculation starting")
    
    listOfFramesToSave = []
    framesToKeep = [i for i in range(0, lastFrame - 1, int((lastFrame - 1) / historyLength if (lastFrame - 1) / historyLength >= 1 else 1))]
    cap.set(1, 0)
    for i in range(0, lastFrame):
      ret, frame = cap.read()
      if i in framesToKeep and ret:
        print(i, lastFrame)
        frame = cv2.resize(frame, (int(frame_width * reduceImageResolutionPercentage), int(frame_height * reduceImageResolutionPercentage)), interpolation = cv2.INTER_AREA)
        listOfFramesToSave.append(frame)
    
    listOfFramesToSave.reverse()
    
    for i in range(0, len(listOfFramesToSave)):
      print("calculating background, currently at frame:", i)
      frame = listOfFramesToSave[i]
      fgmask = fgbg.apply(frame)
    
    # listOfFramesToSave = []
    # for i in range(0, lastFrame - 1, int((lastFrame - 1) / historyLength if (lastFrame - 1) / historyLength >= 1 else 1))]
      # cap.set(1, lastFrame - 1 - i)
      # print("calculating background, currently at frame:", lastFrame - 1 - i)
      # ret, frame = cap.read()
      # if ret:
        # frame = cv2.resize(frame, (int(frame_width * reduceImageResolutionPercentage), int(frame_height * reduceImageResolutionPercentage)), interpolation = cv2.INTER_AREA)
        # fgmask = fgbg.apply(frame)
        # listOfFramesToSave.append(frame)
    cap.release()
    with open(os.path.join(pathToVideo, videoName + '_BackgroundKNN_' + str(historyLength) + '.pkl'), 'wb') as handle:
      pickle.dump(listOfFramesToSave, handle) #, protocol=pickle.HIGHEST_PROTOCOL)
  
  cap = zzVideoReading.VideoCapture(videoPath)
  
  i = firstFrame
  cap.set(1, firstFrame)
  
  while i < lastFrame:
    
    print(i, lastFrame)
    
    ret, frame = cap.read()
    
    if ret:
    
      frameInitialImage = frame.copy()
      
      if hyperparameters["reduceImageResolutionPercentage"]:
        frame = cv2.resize(frame, (int(frame_width * hyperparameters["reduceImageResolutionPercentage"]), int(frame_height * hyperparameters["reduceImageResolutionPercentage"])), interpolation = cv2.INTER_AREA)
        frameInitialImage = frame.copy()
      
      if i == firstFrame:
        
        previousCenterDetectedX, previousCenterDetectedY = util.getPoint(frame, "Click on the center of the head of the animal", zoomable=True, dialog=True)
        tailTipX, tailTipY = util.getPoint(frame, "Click on the tip of the tail of the same animal", zoomable=True, dialog=True)
        
        frame2 = frame.copy()
        frame2 = fgbg.apply(frame2)
        ret, frame2 = cv2.threshold(frame2, 0, 255, cv2.THRESH_BINARY)
        frame2 = fillWhiteHoles(frame2)
        frame2 = 255 - frame2
        if iterativelyErodeEachImage:
          frame2 = erodeThenAddWhiteBorders(frame2, kernel)
        else:
          frame2 = addWhiteBorders(frame2)
        contours, hierarchy = cv2.findContours(frame2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
          if cv2.pointPolygonTest(contour, (previousCenterDetectedX, previousCenterDetectedY), False) >= 0:
            animalBodyArea = cv2.contourArea(contour)
            ROIHalfDiam = int(math.sqrt(animalBodyArea) * 4)
        print("animalBodyArea:", animalBodyArea)
        print("ROIHalfDiam:", ROIHalfDiam)
        if showFramesForDebugging:
          util.showFrame(frame2, title='frame0')
      
      if chooseValueForAnimalBodyArea > 0:
        animalBodyArea = chooseValueForAnimalBodyArea
      
      if ROIHalfDiam == -1:
        raise CustomError("An error occurred")
      
      diffAreaAuthorized = 0.5
      hyperparameters["minAreaBody"] = int(animalBodyArea - animalBodyArea * diffAreaAuthorized)
      hyperparameters["maxAreaBody"] = int(animalBodyArea + animalBodyArea * diffAreaAuthorized)
      hyperparameters["minArea"] = int(animalBodyArea - animalBodyArea * diffAreaAuthorized)
      hyperparameters["maxArea"] = int(animalBodyArea + animalBodyArea * diffAreaAuthorized)
      hyperparameters["headSize"]    = int(math.sqrt(animalBodyArea) * 2)
      hyperparameters["minTailSize"] = int(math.sqrt(animalBodyArea) * 0.5)
      hyperparameters["maxTailSize"] = int(math.sqrt(animalBodyArea) * 4)
      
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
      
      frame = fillWhiteHoles(frame)
      
      frame = 255 - frame
      
      countNbOfRightArea = 0
      distanceToPreviousCenterDetected = 100000000000000000000
      countNbTries = 0
      newCenterDetectedX_ROICordinates = previousCenterDetectedXROICoordinates
      newCenterDetectedY_ROICordinates = previousCenterDetectedYROICoordinates
      mostLikelyContour = 0
      while countNbOfRightArea == 0 and countNbTries < 10:
        countNbTries = countNbTries + 1
        if iterativelyErodeEachImage:
          frame = erodeThenAddWhiteBorders(frame, kernel)
        else:
          frame = addWhiteBorders(frame)
        if showFramesForDebugging:
          util.showFrame(frame, title='frame1')
        
        nbOfIterations = 1
        while cv2.countNonZero(255 - frame) < animalBodyArea and nbOfIterations < 10:
          print("try " + str(nbOfIterations))
          frame = erodeThenDilateThenAddWhiteBorders(frame, kernel, nbOfIterations)
          nbOfIterations += 1
          if showFramesForDebugging:
            util.showDialog(frame, title='frame%d' % str(nbOfIterations))
        
        if nbOfIterations > 1:
          dist2t = fgbg.getDist2Threshold()
          fgbg.setDist2Threshold(dist2t - dist2t * 0.1)
          print("dist2t set to a smaller value:", dist2t - dist2t * 0.1)
        else:
          if cv2.countNonZero(255 - frame) > 1.5 * animalBodyArea:
            dist2t = fgbg.getDist2Threshold()
            fgbg.setDist2Threshold(dist2t + dist2t * 0.1)
            print("dist2t set to a bigger value:", dist2t + dist2t * 0.1)
        
        contours, hierarchy = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
          contourArea = cv2.contourArea(contour)
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
        
        if not(iterativelyErodeEachImage):
          countNbTries = 10
        # print("First: newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates:", newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates)
        
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
                if contourArea > largestContourArea and contourArea < (len(blankPreviousIteration)*len(blankPreviousIteration[0])) * 0.8:
                  largestContourArea = contourArea
                  M = cv2.moments(contour)
                  x = int(M['m10']/M['m00'])
                  y = int(M['m01']/M['m00'])
                  # if False:
                    # [newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates] = reajustCenterOfMassIfNecessary(contour, x, y, len(blankPreviousIteration[0]), len(blankPreviousIteration))
                  newCenterDetectedX_ROICordinates = x
                  newCenterDetectedY_ROICordinates = y
      
      # print("Second: newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates:", newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates)
      
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
