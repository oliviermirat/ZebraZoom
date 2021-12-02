import math
import cv2
import numpy as np
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.calculateHeading import calculateHeadingSimple, calculateHeading

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
    if True:
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
  
def findCenterByIterativelyDilating(initialContour, lenX, lenY):
  x = 0
  y = 0
  image = np.zeros((lenY, lenX))
  image[:, :] = 255
  image = image.astype(np.uint8)
  kernel  = np.ones((3, 3), np.uint8)
  if type(initialContour) != int:
    cv2.fillPoly(image, pts =[initialContour], color=(0))
    image[:,0] = 255
    image[0,:] = 255
    image[:, len(image[0])-1] = 255
    image[len(image)-1, :]    = 255
    nbBlackPixels = 1
    dilateIter = 0
    while nbBlackPixels > 0:
      dilateIter   = dilateIter + 1
      dilatedImage = cv2.dilate(image, kernel, iterations=dilateIter)
      nbBlackPixels = cv2.countNonZero(255-dilatedImage)
    dilateIter   = dilateIter - 1
    dilatedImage = cv2.dilate(image, kernel, iterations=dilateIter)
    dilatedImage[:,0] = 255
    dilatedImage[0,:] = 255
    dilatedImage[:, len(dilatedImage[0])-1] = 255
    dilatedImage[len(dilatedImage)-1, :]    = 255
    contours, hierarchy = cv2.findContours(dilatedImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    maxContour = 0
    maxContourArea = 0
    for contour in contours:
      contourArea = cv2.contourArea(contour)
      if contourArea < int(lenX * lenY * 0.8):
        if contourArea > maxContourArea:
          maxContourArea = contourArea
          maxContour     = contour
    M = cv2.moments(maxContour)
    if M['m00']:
      x = int(M['m10']/M['m00'])
      y = int(M['m01']/M['m00'])
  return [x, y]
   

def multipleAnimalsHeadTracking(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, hyperparameters, gray, i, firstFrame, thresh1, xmin=0, ymin=0):
  
  headCoordinatesOptions      = []
  headCoordinatesAreasOptions = []
  x = 0
  y = 0
  minAreaCur = hyperparameters["minArea"]
  maxAreaCur = hyperparameters["maxArea"]
  meanArea   = (hyperparameters["minArea"] + hyperparameters["maxArea"]) / 2
  
  thresh2 = thresh1.copy()
  erodeSize = hyperparameters["erodeSize"]
  if erodeSize:
    kernel  = np.ones((erodeSize,erodeSize), np.uint8)
    thresh2 = cv2.dilate(thresh2, kernel, iterations=hyperparameters["dilateIter"])
  
  thresh2[:,0] = 255
  thresh2[0,:] = 255
  thresh2[:, len(thresh2[0])-1] = 255
  thresh2[len(thresh2)-1, :]    = 255
  
  if hyperparameters["multipleHeadTrackingIterativelyRelaxAreaCriteria"]:
    contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    areaDecreaseFactor = int(hyperparameters["minArea"]/10)
    while (len(headCoordinatesOptions) < hyperparameters["nbAnimalsPerWell"]) and (minAreaCur > 0):
      headCoordinatesOptions = []
      headCoordinatesAreasOptions = []
      for contour in contours:
        area = cv2.contourArea(contour)
        if (area > minAreaCur) and (area < maxAreaCur):
          if hyperparameters["findCenterOfAnimalByIterativelyDilating"]:
            [x, y] = findCenterByIterativelyDilating(contour, len(thresh2[0]), len(thresh2))
          else:
            M = cv2.moments(contour)
            if M['m00']:
              x = int(M['m10']/M['m00'])
              y = int(M['m01']/M['m00'])
            else:
              x = 0
              y = 0
            if hyperparameters["readjustCenterOfMassIfNotInsideContour"]:
              [x, y] = reajustCenterOfMassIfNecessary(contour, x, y, len(thresh2[0]), len(thresh2))
          if not([x, y] in headCoordinatesOptions):
            headCoordinatesOptions.append([x+xmin, y+ymin])
            headCoordinatesAreasOptions.append(abs(area - (meanArea/2)))
      
      if areaDecreaseFactor:
        minAreaCur = minAreaCur - areaDecreaseFactor
        maxAreaCur = int(maxAreaCur * 1.1)
      else:
        minAreaCur = minAreaCur - 1
        maxAreaCur = int(maxAreaCur * 1.1)
  else:
    contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
      area = cv2.contourArea(contour)
      if (area > minAreaCur) and (area < maxAreaCur):
        # print("Find center of mass: area:", area)
        if hyperparameters["findCenterOfAnimalByIterativelyDilating"]:
          [x, y] = findCenterByIterativelyDilating(contour, len(thresh2[0]), len(thresh2))
        else:
          M = cv2.moments(contour)
          if M['m00']:
            x = int(M['m10']/M['m00'])
            y = int(M['m01']/M['m00'])
          else:
            x = 0
            y = 0
          if hyperparameters["readjustCenterOfMassIfNotInsideContour"]:
            [x, y] = reajustCenterOfMassIfNecessary(contour, x, y, len(thresh2[0]), len(thresh2))
        headCoordinatesOptions.append([x+xmin, y+ymin])
        headCoordinatesAreasOptions.append(abs(area - (meanArea/2)))

  headCoordinatesAreasOptionsSorted = np.argsort(headCoordinatesAreasOptions)
  headCoordinatesOptions = [headCoordinatesOptions[elem] for elem in headCoordinatesAreasOptionsSorted]
  
  headCoordinatesOptionsAlreadyTakenDist     = [-1 for k in headCoordinatesOptions]
  headCoordinatesOptionsAlreadyTakenAnimalId = [-1 for k in headCoordinatesOptions]
  animalNotPutOrEjectedBecausePositionAlreadyTaken = 1
  if i > firstFrame:
    while animalNotPutOrEjectedBecausePositionAlreadyTaken:
      animalNotPutOrEjectedBecausePositionAlreadyTaken = 0
      for animal_Id in range(0, hyperparameters["nbAnimalsPerWell"]):
        x_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-firstFrame-1][0][0]
        y_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-firstFrame-1][0][1]
        x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0]
        y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1]
        if ((x_prevFrame_animal_Id != 0) and (y_prevFrame_animal_Id != 0) and (x_curFrame_animal_Id == 0) and (y_curFrame_animal_Id == 0)):
          min_dist  = 10000000000000000000000
          index_min = -1
          for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
            dist = (idx_x_Option - x_prevFrame_animal_Id)**2 + (idx_y_Option - y_prevFrame_animal_Id)**2
            if dist < min_dist:
              if headCoordinatesOptionsAlreadyTakenDist[idxCoordinateOption] != -1:
                if dist < headCoordinatesOptionsAlreadyTakenDist[idxCoordinateOption]:
                  min_dist = dist
                  index_min = idxCoordinateOption
              else:
                min_dist = dist
                index_min = idxCoordinateOption
          # if len(headCoordinatesOptions):
          if index_min >= 0:
            if (headCoordinatesOptionsAlreadyTakenDist[index_min] == -1):
              # Save position of animal for frame i-firstFrame
              trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] = headCoordinatesOptions[index_min][0]
              trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] = headCoordinatesOptions[index_min][1]     
              headCoordinatesOptionsAlreadyTakenDist[index_min]     = min_dist
              headCoordinatesOptionsAlreadyTakenAnimalId[index_min] = animal_Id
            else:
              animalNotPutOrEjectedBecausePositionAlreadyTaken = 1
              if min_dist < headCoordinatesOptionsAlreadyTakenDist[index_min]:
                # "Ejecting" previously saved position of animal for frame i-firstFrame
                animal_Id_Eject = headCoordinatesOptionsAlreadyTakenAnimalId[index_min]
                trackingHeadTailAllAnimals[animal_Id_Eject, i-firstFrame][0][0] = 0
                trackingHeadTailAllAnimals[animal_Id_Eject, i-firstFrame][0][1] = 0          
                # Replace position of animal for frame i-firstFrame
                trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] = headCoordinatesOptions[index_min][0]
                trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] = headCoordinatesOptions[index_min][1]  
                headCoordinatesOptionsAlreadyTakenDist[index_min]     = min_dist
                headCoordinatesOptionsAlreadyTakenAnimalId[index_min] = animal_Id               
  
  headCoordinatesOptions = [headCoordinatesOptions[idx] for idx, k in enumerate(headCoordinatesOptionsAlreadyTakenAnimalId) if k == -1]
  
  for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
    for animal_Id in range(0, hyperparameters["nbAnimalsPerWell"]):
      if (trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] == 0):
        if i == firstFrame:
          trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] = idx_x_Option
          trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] = idx_y_Option
          break
        else:
          if (trackingHeadTailAllAnimals[animal_Id, i-firstFrame-1][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame-1][0][1] == 0): # NEW !!!!
            trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] = idx_x_Option
            trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] = idx_y_Option
            break

  if hyperparameters["postProcessMultipleTrajectories"]:
    maxDistanceAuthorized = hyperparameters["postProcessMaxDistanceAuthorized"]
    maxDisapearanceFrames = hyperparameters["postProcessMaxDisapearanceFrames"]
    for animal_Id in range(0, len(trackingHeadTailAllAnimals)):
      goBackFrames = 1
      xCur = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0]
      yCur = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1]
      if xCur != 0 or yCur != 0:
        while (i-firstFrame-goBackFrames >= 0) and (goBackFrames < maxDisapearanceFrames) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame-goBackFrames][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame-goBackFrames][0][1] == 0):
          goBackFrames = goBackFrames + 1
        if (goBackFrames < maxDisapearanceFrames) and (i-firstFrame-goBackFrames >= 0):
          xBef = trackingHeadTailAllAnimals[animal_Id, i-firstFrame-goBackFrames][0][0]
          yBef = trackingHeadTailAllAnimals[animal_Id, i-firstFrame-goBackFrames][0][1]
          if math.sqrt((xCur - xBef)**2 + (yCur - yBef)**2) > maxDistanceAuthorized:
            trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] = 0
            trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] = 0
  
  # for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
    # print(i, idxCoordinateOption, idx_x_Option, idx_y_Option)
    # min_dist  = 10000000000000000000000
    # index_min_animal_Id = -1
    # maxdepth_min_animal_Id = 0
    # index_animal_Id_alwaysBeenAt0 = -1
    # for animal_Id in range(0, hyperparameters["nbAnimalsPerWell"]):
      # if (trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1] == 0):
        # depth = 1
        # while (i - firstFrame - depth >= 0) and (depth < 20) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame-depth][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-firstFrame-depth][0][1] == 0):
          # depth = depth + 1
        # xPast_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-firstFrame-depth][0][0]
        # yPast_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-firstFrame-depth][0][1]
        # if (xPast_animal_Id != 0) or (yPast_animal_Id != 0):
          # print("animal_Id:", animal_Id, "; (xPast_animal_Id, yPast_animal_Id):", xPast_animal_Id, yPast_animal_Id)
          # dist = math.sqrt((idx_x_Option - xPast_animal_Id)**2 + (idx_y_Option - yPast_animal_Id)**2)
          # print("dist:", dist)
          # if dist < 30:
            # print("depth", depth)
            # if dist < min_dist:
              # min_dist = dist
              # index_min_animal_Id = animal_Id
              # maxdepth_min_animal_Id = depth
        # else:
          # if index_animal_Id_alwaysBeenAt0 == -1:
            # index_animal_Id_alwaysBeenAt0 = animal_Id
    # print("index_min_animal_Id:", index_min_animal_Id)
    # if index_min_animal_Id >= 0:
      # trackingHeadTailAllAnimals[index_min_animal_Id, i-firstFrame][0][0] = idx_x_Option
      # trackingHeadTailAllAnimals[index_min_animal_Id, i-firstFrame][0][1] = idx_y_Option
      # x_maxPast_animal_Id = trackingHeadTailAllAnimals[index_min_animal_Id, i-firstFrame-maxdepth_min_animal_Id][0][0]
      # y_maxPast_animal_Id = trackingHeadTailAllAnimals[index_min_animal_Id, i-firstFrame-maxdepth_min_animal_Id][0][1]
      # print("x_maxPast_animal_Id, y_maxPast_animal_Id:", x_maxPast_animal_Id, y_maxPast_animal_Id)
      # print("maxdepth_min_animal_Id", maxdepth_min_animal_Id)
      # x_step = (idx_x_Option - x_maxPast_animal_Id) / maxdepth_min_animal_Id
      # y_step = (idx_y_Option - y_maxPast_animal_Id) / maxdepth_min_animal_Id
      # for blankSpace in range(1, maxdepth_min_animal_Id):
        # trackingHeadTailAllAnimals[index_min_animal_Id, i-firstFrame-maxdepth_min_animal_Id+blankSpace][0][0] = x_maxPast_animal_Id + blankSpace * x_step
        # trackingHeadTailAllAnimals[index_min_animal_Id, i-firstFrame-maxdepth_min_animal_Id+blankSpace][0][1] = y_maxPast_animal_Id + blankSpace * y_step
    # else:
      # if index_animal_Id_alwaysBeenAt0 != -1:
        # trackingHeadTailAllAnimals[index_animal_Id_alwaysBeenAt0, i-firstFrame][0][0] = idx_x_Option
        # trackingHeadTailAllAnimals[index_animal_Id_alwaysBeenAt0, i-firstFrame][0][1] = idx_y_Option
  
  if hyperparameters["findCenterOfAnimalByIterativelyDilating"] == 0 or hyperparameters["trackTail"] == 0:
    for animal_Id in range(0, hyperparameters["nbAnimalsPerWell"]):
      x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0]
      y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1]
      if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
        x_curFrame_animal_Id = int(x_curFrame_animal_Id)
        y_curFrame_animal_Id = int(y_curFrame_animal_Id)
        
        # Removing the other blobs from the image to get good heading detection
        # Performance improvement possible below: TODO in the future
        correspondingContour = 0
        contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
          dist = cv2.pointPolygonTest(contour, (x_curFrame_animal_Id, y_curFrame_animal_Id), True)
          if dist >= 0:
            correspondingContour = contour
        thresh2bis = np.zeros((len(thresh2), len(thresh2[0])))
        thresh2bis[:, :] = 255
        if type(correspondingContour) != int:
          cv2.fillPoly(thresh2bis, pts =[correspondingContour], color=(0, 0, 0))
        
        if hyperparameters["forceBlobMethodForHeadTracking"]: # Fish tracking, usually
          previousFrameHeading = trackingHeadingAllAnimals[animal_Id, i-firstFrame-1] if i-firstFrame-1 > 0 else 0
          [heading, lastFirstTheta] = calculateHeading(x_curFrame_animal_Id, y_curFrame_animal_Id, 0, thresh1, thresh2bis, 0, hyperparameters, previousFrameHeading)
        else: # Drosophilia, mouse, and other center of mass only tracking
          heading = calculateHeadingSimple(x_curFrame_animal_Id, y_curFrame_animal_Id, thresh2bis, hyperparameters)
        
        trackingHeadingAllAnimals[animal_Id, i-firstFrame] = heading
  
  return [trackingHeadingAllAnimals, trackingHeadTailAllAnimals]
