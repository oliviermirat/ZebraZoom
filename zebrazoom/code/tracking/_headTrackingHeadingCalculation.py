import math

import cv2
import numpy as np


class HeadTrackingHeadingCalculationMixin:
  def _calculateMinDistFromOtherAnimals(self, animal_Id, trackingHeadTailAllAnimals, i):
    mindist   = 1000000
    for animal_Id2 in range(0, self._hyperparameters["nbAnimalsPerWell"]):
      x_curFrame_animal_Id   = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
      y_curFrame_animal_Id   = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
      if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
        if animal_Id != animal_Id2:
          x_curFrame_animal_Id2  = trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][0]
          y_curFrame_animal_Id2  = trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][1]
          dist = math.sqrt((x_curFrame_animal_Id-x_curFrame_animal_Id2)**2 + (y_curFrame_animal_Id-y_curFrame_animal_Id2)**2)
          if dist < mindist:
            mindist = dist
    return mindist

  def _multipleAnimalsHeadTrackingAdvance(self, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, gray, i, thresh1, thresh3, lengthX):
    marginX = self._hyperparameters["multipleAnimalTrackingAdvanceAlgorithmMarginX"]

    headCoordinatesOptions    = []
    headCoordinatesOptionsAlt = []
    x = 0
    y = 0
    minAreaCur = self._hyperparameters["minArea"]
    maxAreaCur = self._hyperparameters["maxArea"]

    ret,thresh2 = cv2.threshold(gray,self._hyperparameters["thresholdForBlobImg"],255,cv2.THRESH_BINARY)
    erodeSize = self._hyperparameters["erodeSize"]
    kernel  = np.ones((erodeSize,erodeSize), np.uint8)
    thresh2 = cv2.dilate(thresh2, kernel, iterations=self._hyperparameters["dilateIter"])

    thresh2[:,0] = 255
    thresh2[0,:] = 255
    thresh2[:, len(thresh2[0])-1] = 255
    thresh2[len(thresh2)-1, :]    = 255

    # print("frame:", i)
    # cv2.imshow('Frame', thresh2)
    # cv2.waitKey(0)

    if self._hyperparameters["multipleHeadTrackingIterativelyRelaxAreaCriteria"]:
      contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
      while (len(headCoordinatesOptions) < self._hyperparameters["nbAnimalsPerWell"]) and (minAreaCur > 0):
        # print("MMMinAreaCur:", minAreaCur)
        for contour in contours:
          area = cv2.contourArea(contour)
          # if area > 100:
            # print("area:", area)
          if (area > minAreaCur) and (area < maxAreaCur):
            M = cv2.moments(contour)
            if M['m00']:
              x = int(M['m10']/M['m00'])
              y = int(M['m01']/M['m00'])
            else:
              x = 0
              y = 0
            if not([x, y] in headCoordinatesOptions):
              headCoordinatesOptions.append([x, y])
        minAreaCur = minAreaCur - int(self._hyperparameters["minArea"]/10)
        maxAreaCur = maxAreaCur + int(self._hyperparameters["minArea"]/10)
    else:
      contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        area = cv2.contourArea(contour)
        if (area > minAreaCur) and (area < maxAreaCur):
          M = cv2.moments(contour)
          if M['m00']:
            x = int(M['m10']/M['m00'])
            y = int(M['m01']/M['m00'])
            # if area < 600:
            headCoordinatesOptions.append([x, y])
            # else:
              # (xE,yE),(MA,ma),angle = cv2.fitEllipse(contour)
              # r = MA * 0.8
              # headCoordinatesOptions.append([int(xE + r*math.cos((math.pi/2)+angle*(math.pi/180))), int(yE + r*math.sin((math.pi/2)+angle*(math.pi/180)))])
              # headCoordinatesOptions.append([int(xE - r*math.cos((math.pi/2)+angle*(math.pi/180))), int(yE - r*math.sin((math.pi/2)+angle*(math.pi/180)))])
          # else:
            # x = 0
            # y = 0
            # headCoordinatesOptions.append([x, y])
      # Alternative head coordinates options
      for contour in contours:
        area = cv2.contourArea(contour)
        if (area > minAreaCur) and (area < maxAreaCur) and (len(contour) > 4):
          M = cv2.moments(contour)
          if M['m00']:
            x = int(M['m10']/M['m00'])
            y = int(M['m01']/M['m00'])
            (xE,yE),(MA,ma),angle = cv2.fitEllipse(contour)
            r = MA * 0.8
            headCoordinatesOptionsAlt.append([int(xE + r*math.cos((math.pi/2)+angle*(math.pi/180))), int(yE + r*math.sin((math.pi/2)+angle*(math.pi/180))), x, y, int(xE - r*math.cos((math.pi/2)+angle*(math.pi/180))), int(yE - r*math.sin((math.pi/2)+angle*(math.pi/180)))])
            headCoordinatesOptionsAlt.append([int(xE - r*math.cos((math.pi/2)+angle*(math.pi/180))), int(yE - r*math.sin((math.pi/2)+angle*(math.pi/180))), x, y, int(xE + r*math.cos((math.pi/2)+angle*(math.pi/180))), int(yE + r*math.sin((math.pi/2)+angle*(math.pi/180)))])
        else:
          if (area > 0) and (area <= minAreaCur):
            M = cv2.moments(contour)
            if M['m00']:
              x = int(M['m10']/M['m00'])
              y = int(M['m01']/M['m00'])
              headCoordinatesOptionsAlt.append([x, y, -1, -1, -1, -1])

    headCoordinatesOptionsAlreadyTakenDist     = [-1 for k in headCoordinatesOptions]
    headCoordinatesOptionsAlreadyTakenAnimalId = [-1 for k in headCoordinatesOptions]
    animalNotPutOrEjectedBecausePositionAlreadyTaken = 1
    if i > self._firstFrame:
      while animalNotPutOrEjectedBecausePositionAlreadyTaken:
        animalNotPutOrEjectedBecausePositionAlreadyTaken = 0
        for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          x_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][0]
          y_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][1]
          x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
          y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
          if ((x_prevFrame_animal_Id != 0) and (y_prevFrame_animal_Id != 0) and (x_curFrame_animal_Id == 0) and (y_curFrame_animal_Id == 0)):
            min_dist  = 10000000000000000000000
            index_min = -1
            for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
              dist = math.sqrt((idx_x_Option - x_prevFrame_animal_Id)**2 + (idx_y_Option - y_prevFrame_animal_Id)**2)
              if dist < min_dist and (dist < self._hyperparameters["multipleAnimalTrackingAdvanceAlgorithmDist1"] or (dist < self._hyperparameters["multipleAnimalTrackingAdvanceAlgorithmDist2"] and idx_x_Option > marginX and idx_x_Option < lengthX - marginX)):
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
                # Save position of animal for frame i-self._firstFrame
                trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = headCoordinatesOptions[index_min][0]
                trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = headCoordinatesOptions[index_min][1]
                headCoordinatesOptionsAlreadyTakenDist[index_min]     = min_dist
                headCoordinatesOptionsAlreadyTakenAnimalId[index_min] = animal_Id
              else:
                animalNotPutOrEjectedBecausePositionAlreadyTaken = 1
                if min_dist < headCoordinatesOptionsAlreadyTakenDist[index_min]:
                  # "Ejecting" previously saved position of animal for frame i-self._firstFrame
                  animal_Id_Eject = headCoordinatesOptionsAlreadyTakenAnimalId[index_min]
                  trackingHeadTailAllAnimals[animal_Id_Eject, i-self._firstFrame][0][0] = 0
                  trackingHeadTailAllAnimals[animal_Id_Eject, i-self._firstFrame][0][1] = 0
                  # Replace position of animal for frame i-self._firstFrame
                  trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = headCoordinatesOptions[index_min][0]
                  trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = headCoordinatesOptions[index_min][1]
                  headCoordinatesOptionsAlreadyTakenDist[index_min]     = min_dist
                  headCoordinatesOptionsAlreadyTakenAnimalId[index_min] = animal_Id

    headCoordinatesOptions = [headCoordinatesOptions[idx] for idx, k in enumerate(headCoordinatesOptionsAlreadyTakenAnimalId) if k == -1]

    for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
      for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        if (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] == 0):
          if i == self._firstFrame:
            trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = idx_x_Option
            trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = idx_y_Option
            break
          else:
            if (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][1] == 0): # NEW !!!!
              trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = idx_x_Option
              trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = idx_y_Option
              break

    # Rescuing disparitions in the middle of the thing
    if i > self._firstFrame:
      for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        x_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][0]
        y_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][1]
        x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
        y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
        if ((x_prevFrame_animal_Id != 0) and (y_prevFrame_animal_Id != 0) and (x_curFrame_animal_Id == 0) and (y_curFrame_animal_Id == 0) and (x_prevFrame_animal_Id > marginX) and (x_prevFrame_animal_Id < lengthX - marginX) ):
          print("frame:", i, " ; animal:", animal_Id, " has disapeared, looking for alternative")
          min_dist  = 10000000000
          index_min = - 1
          for idxCoordinateOption, [idx_x_Option, idx_y_Option, no1, no1, no3, no4] in enumerate(headCoordinatesOptionsAlt):
            dist = math.sqrt((idx_x_Option - x_prevFrame_animal_Id)**2 + (idx_y_Option - y_prevFrame_animal_Id)**2)
            if dist < min_dist and (dist < self._hyperparameters["multipleAnimalTrackingAdvanceAlgorithmDist1"] or (dist < self._hyperparameters["multipleAnimalTrackingAdvanceAlgorithmDist2"] and idx_x_Option > marginX and idx_x_Option < lengthX - marginX)):
              min_dist = dist
              index_min = idxCoordinateOption
          print("index_min:", index_min)
          mindistFromOtherAnimals = self._calculateMinDistFromOtherAnimals(animal_Id, trackingHeadTailAllAnimals, i)
          if index_min != -1 and mindistFromOtherAnimals >= 5:
            print("coord:", headCoordinatesOptionsAlt[index_min][0], headCoordinatesOptionsAlt[index_min][1], headCoordinatesOptionsAlt[index_min][2], headCoordinatesOptionsAlt[index_min][3], headCoordinatesOptionsAlt[index_min][4], headCoordinatesOptionsAlt[index_min][5])
            trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = headCoordinatesOptionsAlt[index_min][0]
            trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = headCoordinatesOptionsAlt[index_min][1]
            # THIS BELLOW IS NEW !!!
            if headCoordinatesOptionsAlt[index_min][2] != -1: # this alt head option is coming from a blob split in half
              for animal_Id2 in range(0, self._hyperparameters["nbAnimalsPerWell"]):
                alt_assigned_x = headCoordinatesOptionsAlt[index_min][0]
                alt_assigned_y = headCoordinatesOptionsAlt[index_min][1]
                alt_center_x   = headCoordinatesOptionsAlt[index_min][2]
                alt_center_y   = headCoordinatesOptionsAlt[index_min][3]
                alt_opo_x      = headCoordinatesOptionsAlt[index_min][4]
                alt_opo_y      = headCoordinatesOptionsAlt[index_min][5]
                if animal_Id2 != animal_Id:
                  otherAnimal_x = trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][0]
                  otherAnimal_y = trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][1]
                  if (otherAnimal_x == alt_center_x and otherAnimal_y == alt_center_y) or (otherAnimal_x == alt_assigned_x and otherAnimal_y == alt_assigned_y):
                    print("yeah!!! changed!!", (otherAnimal_x == alt_center_x and otherAnimal_y == alt_center_y), (otherAnimal_x == alt_assigned_x and otherAnimal_y == alt_assigned_y))
                    trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][0] = alt_opo_x
                    trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][1] = alt_opo_y
                  break

    # Remove doublons
    if i > self._firstFrame:
      for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        # mindist   = 1000000
        # for animal_Id2 in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          # x_curFrame_animal_Id   = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
          # y_curFrame_animal_Id   = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
          # if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
            # if animal_Id != animal_Id2:
              # x_curFrame_animal_Id2  = trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][0]
              # y_curFrame_animal_Id2  = trackingHeadTailAllAnimals[animal_Id2, i-self._firstFrame][0][1]
              # dist = math.sqrt((x_curFrame_animal_Id-x_curFrame_animal_Id2)**2 + (y_curFrame_animal_Id-y_curFrame_animal_Id2)**2)
              # if dist < mindist:
                # mindist = dist
        mindist = self._calculateMinDistFromOtherAnimals(animal_Id, trackingHeadTailAllAnimals, i)
        if mindist < 4:
          print("removed ", trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0], trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1])
          trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = 0
          trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = 0

    count = 0
    if i > self._firstFrame:
      for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
        y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
        if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
          count = count + 1
    print("Frame ", i, "; count: ", count)

    # for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
      # print(i, idxCoordinateOption, idx_x_Option, idx_y_Option)
      # min_dist  = 10000000000000000000000
      # index_min_animal_Id = -1
      # maxdepth_min_animal_Id = 0
      # index_animal_Id_alwaysBeenAt0 = -1
      # for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        # if (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] == 0):
          # depth = 1
          # while (i - self._firstFrame - depth >= 0) and (depth < 20) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][1] == 0):
            # depth = depth + 1
          # xPast_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][0]
          # yPast_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][1]
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
        # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame][0][0] = idx_x_Option
        # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame][0][1] = idx_y_Option
        # x_maxPast_animal_Id = trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id][0][0]
        # y_maxPast_animal_Id = trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id][0][1]
        # print("x_maxPast_animal_Id, y_maxPast_animal_Id:", x_maxPast_animal_Id, y_maxPast_animal_Id)
        # print("maxdepth_min_animal_Id", maxdepth_min_animal_Id)
        # x_step = (idx_x_Option - x_maxPast_animal_Id) / maxdepth_min_animal_Id
        # y_step = (idx_y_Option - y_maxPast_animal_Id) / maxdepth_min_animal_Id
        # for blankSpace in range(1, maxdepth_min_animal_Id):
          # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id+blankSpace][0][0] = x_maxPast_animal_Id + blankSpace * x_step
          # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id+blankSpace][0][1] = y_maxPast_animal_Id + blankSpace * y_step
      # else:
        # if index_animal_Id_alwaysBeenAt0 != -1:
          # trackingHeadTailAllAnimals[index_animal_Id_alwaysBeenAt0, i-self._firstFrame][0][0] = idx_x_Option
          # trackingHeadTailAllAnimals[index_animal_Id_alwaysBeenAt0, i-self._firstFrame][0][1] = idx_y_Option

    for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
      x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
      y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
      if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
        x_curFrame_animal_Id = int(x_curFrame_animal_Id)
        y_curFrame_animal_Id = int(y_curFrame_animal_Id)
        heading = 0 #calculateHeadingSimple(x_curFrame_animal_Id, y_curFrame_animal_Id, thresh2, self._hyperparameters)
        trackingHeadingAllAnimals[animal_Id, i-self._firstFrame] = heading

  @staticmethod
  def __simpleOptimalValueSearch(PtClosest, contour, unitVector, lenX, lenY):

    factor = 0
    dist = 1
    maxDist = 0
    indMax = 0
    testCenter = PtClosest + factor * unitVector
    while (dist > 0) and (factor < 20) and (testCenter[0] >= 0) and (testCenter[1] >= 0) and (testCenter[0] < lenX) and (testCenter[1] < lenY):
      factor = factor + 1
      testCenter = PtClosest + factor * unitVector
      testCenter = testCenter.astype(int)
      dist = cv2.pointPolygonTest(contour, (float(testCenter[0]), float(testCenter[1])), True)
      if dist > maxDist:
        maxDist = dist
        indMax  = factor

    testCenter = PtClosest + indMax * unitVector
    testCenter = testCenter.astype(int)

    return testCenter

  def __reajustCenterOfMassIfNecessary(self, contour, x, y, lenX, lenY):
    inside = cv2.pointPolygonTest(contour, (float(x), float(y)), True)
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
        while (cv2.pointPolygonTest(contour, (float(testCenter[0]), float(testCenter[1])), True) <= 0) and (factor > 1):
          factor = factor - 1
          testCenter = PtClosest + factor * unitVector
      else:
        testCenter = self.__simpleOptimalValueSearch(PtClosest, contour, unitVector, lenX, lenY)

      x = testCenter[0]
      y = testCenter[1]

    return [x, y]

  @staticmethod
  def __findCenterByIterativelyDilating(initialContour, lenX, lenY):
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

  def _multipleAnimalsHeadTracking(self, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, gray, i, thresh1, xmin=0, ymin=0):

    headCoordinatesOptions      = []
    headCoordinatesAreasOptions = []
    x = 0
    y = 0
    minAreaCur = self._hyperparameters["minArea"]
    maxAreaCur = self._hyperparameters["maxArea"]
    meanArea   = (self._hyperparameters["minArea"] + self._hyperparameters["maxArea"]) / 2

    thresh2 = thresh1.copy()
    erodeSize = self._hyperparameters["erodeSize"]
    if erodeSize:
      kernel  = np.ones((erodeSize,erodeSize), np.uint8)
      thresh2 = cv2.dilate(thresh2, kernel, iterations=self._hyperparameters["dilateIter"])

    thresh2[:,0] = 255
    thresh2[0,:] = 255
    thresh2[:, len(thresh2[0])-1] = 255
    thresh2[len(thresh2)-1, :]    = 255

    if self._hyperparameters["multipleHeadTrackingIterativelyRelaxAreaCriteria"]:
      contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
      areaDecreaseFactor = int(self._hyperparameters["minArea"]/10)
      while (len(headCoordinatesOptions) < self._hyperparameters["nbAnimalsPerWell"]) and (minAreaCur > 0):
        headCoordinatesOptions = []
        headCoordinatesAreasOptions = []
        for contour in contours:
          area = cv2.contourArea(contour)
          if (area > minAreaCur) and (area < maxAreaCur):
            if self._hyperparameters["findCenterOfAnimalByIterativelyDilating"]:
              [x, y] = self.__findCenterByIterativelyDilating(contour, len(thresh2[0]), len(thresh2))
            else:
              M = cv2.moments(contour)
              if M['m00']:
                x = int(M['m10']/M['m00'])
                y = int(M['m01']/M['m00'])
              else:
                x = 0
                y = 0
              if self._hyperparameters["readjustCenterOfMassIfNotInsideContour"]:
                [x, y] = self.__reajustCenterOfMassIfNecessary(contour, x, y, len(thresh2[0]), len(thresh2))
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
          if self._hyperparameters["findCenterOfAnimalByIterativelyDilating"]:
            [x, y] = self.__findCenterByIterativelyDilating(contour, len(thresh2[0]), len(thresh2))
          else:
            M = cv2.moments(contour)
            if M['m00']:
              x = int(M['m10']/M['m00'])
              y = int(M['m01']/M['m00'])
            else:
              x = 0
              y = 0
            if self._hyperparameters["readjustCenterOfMassIfNotInsideContour"]:
              [x, y] = self.__reajustCenterOfMassIfNecessary(contour, x, y, len(thresh2[0]), len(thresh2))
          headCoordinatesOptions.append([x+xmin, y+ymin])
          headCoordinatesAreasOptions.append(abs(area - (meanArea/2)))

    headCoordinatesAreasOptionsSorted = np.argsort(headCoordinatesAreasOptions)
    headCoordinatesOptions = [headCoordinatesOptions[elem] for elem in headCoordinatesAreasOptionsSorted]

    headCoordinatesOptionsAlreadyTakenDist     = [-1 for k in headCoordinatesOptions]
    headCoordinatesOptionsAlreadyTakenAnimalId = [-1 for k in headCoordinatesOptions]
    animalNotPutOrEjectedBecausePositionAlreadyTaken = 1
    if i > self._firstFrame:
      while animalNotPutOrEjectedBecausePositionAlreadyTaken:
        animalNotPutOrEjectedBecausePositionAlreadyTaken = 0
        for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          x_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][0]
          y_prevFrame_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][1]
          x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
          y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
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
                # Save position of animal for frame i-self._firstFrame
                trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = headCoordinatesOptions[index_min][0]
                trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = headCoordinatesOptions[index_min][1]
                headCoordinatesOptionsAlreadyTakenDist[index_min]     = min_dist
                headCoordinatesOptionsAlreadyTakenAnimalId[index_min] = animal_Id
              else:
                animalNotPutOrEjectedBecausePositionAlreadyTaken = 1
                if min_dist < headCoordinatesOptionsAlreadyTakenDist[index_min]:
                  # "Ejecting" previously saved position of animal for frame i-self._firstFrame
                  animal_Id_Eject = headCoordinatesOptionsAlreadyTakenAnimalId[index_min]
                  trackingHeadTailAllAnimals[animal_Id_Eject, i-self._firstFrame][0][0] = 0
                  trackingHeadTailAllAnimals[animal_Id_Eject, i-self._firstFrame][0][1] = 0
                  # Replace position of animal for frame i-self._firstFrame
                  trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = headCoordinatesOptions[index_min][0]
                  trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = headCoordinatesOptions[index_min][1]
                  headCoordinatesOptionsAlreadyTakenDist[index_min]     = min_dist
                  headCoordinatesOptionsAlreadyTakenAnimalId[index_min] = animal_Id

    headCoordinatesOptions = [headCoordinatesOptions[idx] for idx, k in enumerate(headCoordinatesOptionsAlreadyTakenAnimalId) if k == -1]

    for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
      for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        if (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] == 0):
          if i == self._firstFrame:
            trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = idx_x_Option
            trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = idx_y_Option
            break
          else:
            if (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-1][0][1] == 0): # NEW !!!!
              trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = idx_x_Option
              trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = idx_y_Option
              break

    if self._hyperparameters["postProcessMultipleTrajectories"]:
      maxDistanceAuthorized = self._hyperparameters["postProcessMaxDistanceAuthorized"]
      maxDisapearanceFrames = self._hyperparameters["postProcessMaxDisapearanceFrames"]
      for animal_Id in range(0, len(trackingHeadTailAllAnimals)):
        goBackFrames = 1
        xCur = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
        yCur = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
        if xCur != 0 or yCur != 0:
          while (i-self._firstFrame-goBackFrames >= 0) and (goBackFrames < maxDisapearanceFrames) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-goBackFrames][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-goBackFrames][0][1] == 0):
            goBackFrames = goBackFrames + 1
          if (goBackFrames < maxDisapearanceFrames) and (i-self._firstFrame-goBackFrames >= 0):
            xBef = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-goBackFrames][0][0]
            yBef = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-goBackFrames][0][1]
            if math.sqrt((xCur - xBef)**2 + (yCur - yBef)**2) > maxDistanceAuthorized:
              trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] = 0
              trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] = 0

    # for idxCoordinateOption, [idx_x_Option, idx_y_Option] in enumerate(headCoordinatesOptions):
      # print(i, idxCoordinateOption, idx_x_Option, idx_y_Option)
      # min_dist  = 10000000000000000000000
      # index_min_animal_Id = -1
      # maxdepth_min_animal_Id = 0
      # index_animal_Id_alwaysBeenAt0 = -1
      # for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        # if (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1] == 0):
          # depth = 1
          # while (i - self._firstFrame - depth >= 0) and (depth < 20) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][0] == 0) and (trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][1] == 0):
            # depth = depth + 1
          # xPast_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][0]
          # yPast_animal_Id = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame-depth][0][1]
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
        # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame][0][0] = idx_x_Option
        # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame][0][1] = idx_y_Option
        # x_maxPast_animal_Id = trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id][0][0]
        # y_maxPast_animal_Id = trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id][0][1]
        # print("x_maxPast_animal_Id, y_maxPast_animal_Id:", x_maxPast_animal_Id, y_maxPast_animal_Id)
        # print("maxdepth_min_animal_Id", maxdepth_min_animal_Id)
        # x_step = (idx_x_Option - x_maxPast_animal_Id) / maxdepth_min_animal_Id
        # y_step = (idx_y_Option - y_maxPast_animal_Id) / maxdepth_min_animal_Id
        # for blankSpace in range(1, maxdepth_min_animal_Id):
          # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id+blankSpace][0][0] = x_maxPast_animal_Id + blankSpace * x_step
          # trackingHeadTailAllAnimals[index_min_animal_Id, i-self._firstFrame-maxdepth_min_animal_Id+blankSpace][0][1] = y_maxPast_animal_Id + blankSpace * y_step
      # else:
        # if index_animal_Id_alwaysBeenAt0 != -1:
          # trackingHeadTailAllAnimals[index_animal_Id_alwaysBeenAt0, i-self._firstFrame][0][0] = idx_x_Option
          # trackingHeadTailAllAnimals[index_animal_Id_alwaysBeenAt0, i-self._firstFrame][0][1] = idx_y_Option

    if self._hyperparameters["findCenterOfAnimalByIterativelyDilating"] == 0 or self._hyperparameters["trackTail"] == 0:
      for animal_Id in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][0]
        y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-self._firstFrame][0][1]
        if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
          x_curFrame_animal_Id = int(x_curFrame_animal_Id)
          y_curFrame_animal_Id = int(y_curFrame_animal_Id)

          # Removing the other blobs from the image to get good heading detection
          # Performance improvement possible below: TODO in the future
          correspondingContour = 0
          contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
          for contour in contours:
            dist = cv2.pointPolygonTest(contour, (float(x_curFrame_animal_Id), float(y_curFrame_animal_Id)), True)
            if dist >= 0:
              correspondingContour = contour
          thresh2bis = np.zeros((len(thresh2), len(thresh2[0])))
          thresh2bis[:, :] = 255
          if type(correspondingContour) != int:
            cv2.fillPoly(thresh2bis, pts =[correspondingContour], color=(0, 0, 0))

          if self._hyperparameters["forceBlobMethodForHeadTracking"]: # Fish tracking, usually
            previousFrameHeading = trackingHeadingAllAnimals[animal_Id, i-self._firstFrame-1] if i-self._firstFrame-1 > 0 else 0
            [heading, lastFirstTheta] = self._calculateHeading(x_curFrame_animal_Id, y_curFrame_animal_Id, 0, thresh1, thresh2bis, 0, previousFrameHeading)
          else: # Drosophilia, mouse, and other center of mass only tracking
            heading = self._calculateHeadingSimple(x_curFrame_animal_Id, y_curFrame_animal_Id, thresh2bis)

          trackingHeadingAllAnimals[animal_Id, i-self._firstFrame] = heading

  def __headTrackingTakeHeadClosestToWellCenter(self, thresh1, thresh2, blur, erodeSize, minArea, maxArea, frame_width, frame_height):
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
    xmin = self._assignValueIfBetweenRange(x - halfDiam, 0, frame_width-1)
    xmax = self._assignValueIfBetweenRange(x + halfDiam, 0, frame_height-1)
    ymin = self._assignValueIfBetweenRange(y - halfDiam, 0, frame_width-1)
    ymax = self._assignValueIfBetweenRange(y + halfDiam, 0, frame_height-1)
    blur[0:ymin, :]              = 255
    blur[ymax:frame_height-1, :] = 255
    blur[:, 0:xmin]              = 255
    blur[:, xmax:frame_width-1]  = 255
    (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)

    return headPosition

  def _headTrackingHeadingCalculation(self, i, blur, thresh1, thresh2, gray, erodeSize, frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPosition, lengthX, xmin=0, ymin=0, wellNumber=-1):
    xHB_TN = 0
    heading = 0
    x = 0
    y = 0
    lastFirstTheta = 0

    if self._hyperparameters["fixedHeadPositionX"] != -1:

      trackingHeadTailAllAnimals[0, i-self._firstFrame][0][0] = int(self._hyperparameters["fixedHeadPositionX"])
      trackingHeadTailAllAnimals[0, i-self._firstFrame][0][1] = int(self._hyperparameters["fixedHeadPositionY"])

    else:

      if self._hyperparameters["nbAnimalsPerWell"] > 1 or self._hyperparameters["forceBlobMethodForHeadTracking"]:

        if self._hyperparameters["multipleAnimalTrackingAdvanceAlgorithm"] == 0:
          self._multipleAnimalsHeadTracking(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, gray, i, thresh1, xmin, ymin)
        else:
          self._multipleAnimalsHeadTrackingAdvance(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, gray, i, thresh1, thresh2, lengthX)

        heading = 0
        headPosition = [0, 0]
        x = 0
        y = 0
        lastFirstTheta = 0

      else:

        if (self._hyperparameters["headEmbeded"] == 1 and i == self._firstFrame) or (self._hyperparameters["headEmbeded"] == 0) or (self._hyperparameters["headEmbededTeresaNicolson"] == 1):

          if self._hyperparameters["findHeadPositionByUserInput"] == 0:

            if type(blur) == int: # it won't be equal to int for images coming from the faster screen 'multiprocessing'
              paramGaussianBlur = int((self._hyperparameters["paramGaussianBlur"] / 2)) * 2 + 1
              blur = cv2.GaussianBlur(gray, (paramGaussianBlur, paramGaussianBlur), 0)

            # Finds head position for frame i
            takeTheHeadClosestToTheCenter = self._hyperparameters["takeTheHeadClosestToTheCenter"]
            if takeTheHeadClosestToTheCenter == 0:
              (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)
              if type(trackingProbabilityOfGoodDetection) != int and len(trackingProbabilityOfGoodDetection) and i-self._firstFrame < len(trackingProbabilityOfGoodDetection[0]):
                trackingProbabilityOfGoodDetection[0, i-self._firstFrame] = np.sum(255 - blur)
            else:
              headPosition = self.__headTrackingTakeHeadClosestToWellCenter(thresh1, thresh2, blur, erodeSize, self._hyperparameters["minArea"], self._hyperparameters["maxArea"], frame_width, frame_height)

            x = headPosition[0]
            y = headPosition[1]

            if (self._hyperparameters["headEmbededTeresaNicolson"] == 1) and (i == self._firstFrame):
              xHB_TN = x

            if (self._hyperparameters["headEmbededTeresaNicolson"] == 1):
              headPosition = [xHB_TN + 100, y]

            if type(headPosition) == tuple:
              headPosition = list(headPosition)
              headPosition[0] = headPosition[0] + xmin
              headPosition[1] = headPosition[1] + ymin
              headPosition = tuple(headPosition)
            else:
              headPosition[0] = headPosition[0] + xmin
              headPosition[1] = headPosition[1] + ymin

            # Calculate heading for frame i
            if type(thresh1) != int:
              [heading, lastFirstTheta] = self._calculateHeading(x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter, 0, wellNumber)

            if (self._hyperparameters["headEmbededTeresaNicolson"] == 1):
              heading = 0
              lastFirstTheta = 0

            trackingHeadTailAllAnimals[0, i-self._firstFrame][0][0] = headPosition[0]
            trackingHeadTailAllAnimals[0, i-self._firstFrame][0][1] = headPosition[1]
            trackingHeadingAllAnimals[0, i-self._firstFrame] = heading

          else:

            # This is for the head-embedeed: at this point, this is set again in the tail tracking (the heading is set in the tail tracking as well)
            trackingHeadTailAllAnimals[0, i-self._firstFrame][0][0] = headPosition[0]
            trackingHeadTailAllAnimals[0, i-self._firstFrame][0][1] = headPosition[1]

        else:
          # If head embeded, heading and head position stay the same for all frames
          trackingHeadingAllAnimals[0, i-self._firstFrame]  = trackingHeadingAllAnimals[0, 0]
          trackingHeadTailAllAnimals[0, i-self._firstFrame] = trackingHeadTailAllAnimals[0, 0]

    return lastFirstTheta
