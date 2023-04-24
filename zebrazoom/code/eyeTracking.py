import math

import cv2
import numpy as np


class _HeadTrackingHeadingCalculationMixin:
  def _computeHeading(self, thresh1, x, y, headSize):
    if headSize == -1:
      print("Setting headSize to 25 instead of -1, this may be a problem in some cases")
      headSize = 25 # This was introduced to fix bug when config file creation for center of mass only tracking 16/11/22

    videoWidth  = self._hyperparameters["videoWidth"]
    videoHeight = self._hyperparameters["videoHeight"]

    x = x + int(headSize)
    y = y + int(headSize)

    paddedImage = np.zeros((len(thresh1) + 2 * int(headSize), len(thresh1[0]) + 2 * int(headSize)))
    paddedImage[:, :] = 255
    paddedImage[int(headSize):len(thresh1)+int(headSize), int(headSize):len(thresh1[0])+int(headSize)] = thresh1
    thresh1 = paddedImage

    thresh1 = thresh1.astype(np.uint8)

    ymin  = y - headSize
    ymax  = y + headSize
    xmin  = x - headSize
    xmax  = x + headSize

    img = thresh1[int(ymin):int(ymax), int(xmin):int(xmax)]

    img[0,:] = 255
    img[len(img)-1,:] = 255
    img[:,0] = 255
    img[:,len(img[0])-1] = 255

    y, x = np.nonzero(img)
    x = x - np.mean(x)
    y = y - np.mean(y)
    coords = np.vstack([x, y])
    cov = np.cov(coords)
    evals, evecs = np.linalg.eig(cov)
    sort_indices = np.argsort(evals)[::-1]
    x_v1, y_v1 = evecs[:, sort_indices[0]]  # Eigenvector with largest eigenvalue
    x_v2, y_v2 = evecs[:, sort_indices[1]]
    scale = 20
    theta = self._calculateAngle(0, 0, x_v1, y_v1)
    theta = (theta - math.pi/2) % (2 * math.pi)

    if self._hyperparameters["debugHeadingCalculation"]:
      img2 = img.copy()
      img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
      cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img[0])/2 + 20 * math.cos(theta)), int(len(img)/2 + 20 * math.sin(theta))), (255,0,0), 1)
      self._debugFrame(img2, title='imgForHeadingCalculation')

    return theta

  def _calculateHeading(self, x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter, previousFrameHeading=0):
    nbList = self._hyperparameters["nbList"]
    expDecreaseFactor = self._hyperparameters["expDecreaseFactor"]
    headSize = self._hyperparameters["headSize"]
    debugTracking = self._hyperparameters["debugTracking"]
    headEmbeded = self._hyperparameters["headEmbeded"]

    if self._hyperparameters["debugHeadingCalculation"]:
      self._debugFrame(thresh1, title='thresh1')
      self._debugFrame(thresh2, title='thresh2')

    cx = 0
    cy = 0
    cxNew = 0
    cyNew = 0

    thresh1[0,:]                 = 255
    thresh1[len(thresh1)-1,:]    = 255
    thresh1[:,0]                 = 255
    thresh1[:,len(thresh1[0])-1] = 255

    contours, hierarchy = cv2.findContours(thresh1,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
      dist = cv2.pointPolygonTest(contour, (x, y), True)
      if dist >= 0:
        M = cv2.moments(contour)
        if M['m00']:
          cx = int(M['m10']/M['m00'])
          cy = int(M['m01']/M['m00'])
          bodyContour = contour
        else:
          cx = 0
          cy = 0
        if self._hyperparameters["debugHeadingCalculation"]:
          print("area:", area)
          print("dist, cx, cy:", dist, cx, cy)
          print("x, y:", x, y)

    if self._hyperparameters["debugHeadingCalculation"]:
      print("x, y, cx, cy:", x, y, cx, cy)

    heading = self._computeHeading(thresh2, x, y, headSize)
    if self._hyperparameters["debugHeadingCalculation"]:
      print("previousFrameHeading:", previousFrameHeading)
      print("math.sqrt((x - cx)**2 + (y - cy)**2):", math.sqrt((x - cx)**2 + (y - cy)**2))
    if math.sqrt((x - cx)**2 + (y - cy)**2) > 1:
      lastFirstTheta = self._calculateAngle(x, y, cx, cy)
    else:
      lastFirstTheta = (previousFrameHeading + math.pi) % (2 * math.pi)

    headingApproximate = lastFirstTheta
    headingPreciseOpt1 = heading
    headingPreciseOpt2 = (heading + math.pi) % (2*math.pi)
    diffAngle1 = self._distBetweenThetas(headingApproximate, headingPreciseOpt1)
    diffAngle2 = self._distBetweenThetas(headingApproximate, headingPreciseOpt2)
    if (diffAngle1 > diffAngle2):
      heading = headingPreciseOpt1
    else:
      heading = headingPreciseOpt2

    if self._hyperparameters["debugHeadingCalculation"]:
      print("headingApproximate:", headingApproximate)
      print("headingPreciseOpt1:", headingPreciseOpt1)
      print("headingPreciseOpt2:", headingPreciseOpt2)
      print("diffAngle1:", diffAngle1)
      print("diffAngle2:", diffAngle2)
      print("heading:", heading)

    return [heading, lastFirstTheta]

  def _calculateHeadingSimple(self, x, y, thresh2):
    headSize = self._hyperparameters["headSize"]
    heading = self._computeHeading(thresh2, x, y, headSize)
    return heading

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
      dist = cv2.pointPolygonTest(contour, (testCenter[0], testCenter[1]), True)
      if dist > maxDist:
        maxDist = dist
        indMax  = factor

    testCenter = PtClosest + indMax * unitVector
    testCenter = testCenter.astype(int)

    return testCenter

  @staticmethod
  def __reajustCenterOfMassIfNecessary(contour, x, y, lenX, lenY):
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

  def _multipleAnimalsHeadTracking(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, gray, i, thresh1, xmin=0, ymin=0):

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
            dist = cv2.pointPolygonTest(contour, (x_curFrame_animal_Id, y_curFrame_animal_Id), True)
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

  @staticmethod
  def __headTrackingTakeHeadClosestToWellCenter(thresh1, thresh2, blur, erodeSize, minArea, maxArea, frame_width, frame_height):
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

  def _headTrackingHeadingCalculation(self, i, blur, thresh1, thresh2, gray, erodeSize, frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPosition, lengthX, xmin=0, ymin=0):
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
              [heading, lastFirstTheta] = self._calculateHeading(x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter)

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


class EyeTrackingMixin(_HeadTrackingHeadingCalculationMixin):
  def _adjustHeadEmbeddedEyeTrackingParamsSegment(self, i, colorFrame, widgets):
    pass

  def _adjustHeadEmbeddedEyeTrackingParamsSegment(self, i, colorFrame, widgets):
    pass

  def _eyeTrackingHeadEmbedded(self, animalId, i, frame, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets=None):
    if self._hyperparameters["eyeTrackingHeadEmbeddedWithSegment"]:
      return self._eyeTrackingHeadEmbeddedSegment(animalId, i, frame, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets)

    if self._hyperparameters["eyeTrackingHeadEmbeddedWithEllipse"]:
      return self._eyeTrackingHeadEmbeddedEllipse(animalId, i, frame, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets)

  def _eyeTrackingHeadEmbeddedSegment(self, animalId, i, frame, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets):
    headingLineHalfDiameter = self._hyperparameters["eyeTrackingHeadEmbeddedHalfDiameter"]
    headingLineWidthLeft    = self._hyperparameters["eyeTrackingHeadEmbeddedWidthLeft"] if self._hyperparameters["eyeTrackingHeadEmbeddedWidthLeft"] else self._hyperparameters["eyeTrackingHeadEmbeddedWidth"]
    headingLineWidthRight   = self._hyperparameters["eyeTrackingHeadEmbeddedWidthRight"] if self._hyperparameters["eyeTrackingHeadEmbeddedWidthRight"] else self._hyperparameters["eyeTrackingHeadEmbeddedWidth"]
    headingLineWidthArray = [headingLineWidthLeft, headingLineWidthRight]

    if self._hyperparameters["improveContrastForEyeDetectionOfHeadEmbedded"]:
      forEye = self.getAccentuateFrameForManualPointSelect(frame) * 255
    else:
      forEye = frame.copy()
    if self._hyperparameters["invertColorsForHeadEmbeddedEyeTracking"]:
      forEye = 255 - forEye

    forEye = forEye.astype(np.uint8)

    angle = []
    for eyeIdx, eyeCoordinate in enumerate([leftEyeCoordinate, rightEyeCoordinate]):
      headingLineWidth = headingLineWidthArray[eyeIdx]
      forSpecificEye = forEye[int(eyeCoordinate[1]-headingLineHalfDiameter):int(eyeCoordinate[1]+headingLineHalfDiameter), int(eyeCoordinate[0]-headingLineHalfDiameter):int(eyeCoordinate[0]+headingLineHalfDiameter)]
      pixelSum  = 0
      bestAngle = 0
      nTries    = 20
      for j in range(0, nTries):
        angleOption = j * (math.pi / nTries)
        startPoint = (int(headingLineHalfDiameter - headingLineHalfDiameter * math.cos(angleOption)), int(headingLineHalfDiameter - headingLineHalfDiameter * math.sin(angleOption)))
        endPoint   = (int(headingLineHalfDiameter + headingLineHalfDiameter * math.cos(angleOption)), int(headingLineHalfDiameter + headingLineHalfDiameter * math.sin(angleOption)))
        testImage  = forSpecificEye.copy()
        testImage  = cv2.line(testImage, startPoint, endPoint, (0), headingLineWidth)
        nbWhitePixels = np.sum(testImage)
        if nbWhitePixels > pixelSum:
          pixelSum  = nbWhitePixels
          bestAngle = angleOption
      bestAngle1 = bestAngle
      nTries2     = 50
      for j2 in range(0, nTries2):
        angleOption = bestAngle1 - ((math.pi / nTries) / 2) + ((j2 / nTries2) * (math.pi / nTries))
        startPoint = (int(headingLineHalfDiameter - headingLineHalfDiameter * math.cos(angleOption)), int(headingLineHalfDiameter - headingLineHalfDiameter * math.sin(angleOption)))
        endPoint   = (int(headingLineHalfDiameter + headingLineHalfDiameter * math.cos(angleOption)), int(headingLineHalfDiameter + headingLineHalfDiameter * math.sin(angleOption)))
        testImage  = forSpecificEye.copy()
        testImage  = cv2.line(testImage, startPoint, endPoint, (0), headingLineWidth)
        nbWhitePixels = np.sum(testImage)
        if nbWhitePixels > pixelSum:
          pixelSum  = nbWhitePixels
          bestAngle = angleOption
      angle.append(bestAngle)

    leftEyeAngle  = angle[0]
    rightEyeAngle = angle[1]

    # Debugging Plot
    if self._hyperparameters["debugEyeTracking"] or self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
      if self._hyperparameters["improveContrastForEyeDetectionOfHeadEmbedded"]:
        forEye2 = self.getAccentuateFrameForManualPointSelect(frame) * 255
      else:
        forEye2 = frame.copy()
      if self._hyperparameters["invertColorsForHeadEmbeddedEyeTracking"]:
        forEye2 = 255 - forEye2
      forEye2 = forEye2.astype(np.uint8)
      colorFrame = forEye2.copy()
      # Left eye
      cv2.circle(colorFrame, (leftEyeCoordinate[0], leftEyeCoordinate[1]), 2, (0,255,255), 1)
      cv2.line(colorFrame, (int(leftEyeCoordinate[0]-headingLineHalfDiameter*math.cos(leftEyeAngle)), int(leftEyeCoordinate[1]-headingLineHalfDiameter*math.sin(leftEyeAngle))), (int(leftEyeCoordinate[0]+headingLineHalfDiameter*math.cos(leftEyeAngle)), int(leftEyeCoordinate[1]+headingLineHalfDiameter*math.sin(leftEyeAngle))), (255,0,255), headingLineWidthLeft)
      # Right eye
      cv2.circle(colorFrame, (rightEyeCoordinate[0], rightEyeCoordinate[1]), 2, (0,255,255), 1)
      cv2.line(colorFrame, (int(rightEyeCoordinate[0]-headingLineHalfDiameter*math.cos(rightEyeAngle)), int(rightEyeCoordinate[1]-headingLineHalfDiameter*math.sin(rightEyeAngle))), (int(rightEyeCoordinate[0]+headingLineHalfDiameter*math.cos(rightEyeAngle)), int(rightEyeCoordinate[1]+headingLineHalfDiameter*math.sin(rightEyeAngle))), (255,0,255), headingLineWidthRight)
      if self._hyperparameters["debugEyeTracking"]:
        self._debugFrame(colorFrame, title='Eye Tracking debugging')
      if self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
        return self._adjustHeadEmbeddedEyeTrackingParamsSegment(i, colorFrame, self._hyperparameters, widgets)

    trackingEyesAllAnimals[animalId, i-self._firstFrame, 0] = leftEyeCoordinate[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 1] = leftEyeCoordinate[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 2] = leftEyeAngle
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 3] = 0
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 4] = rightEyeCoordinate[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 5] = rightEyeCoordinate[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 6] = rightEyeAngle
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 7] = 0

  def _eyeTrackingHeadEmbeddedEllipse(self, animalId, i, frame, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets):
    if self._hyperparameters["improveContrastForEyeDetectionOfHeadEmbedded"]:
      forEye = self.getAccentuateFrameForManualPointSelect(frame) * 255
    else:
      forEye = frame.copy()
    if self._hyperparameters["invertColorsForHeadEmbeddedEyeTracking"]:
      forEye = 255 - forEye

    forEye = forEye.astype(np.uint8)

    eyeBinaryThreshold = self._hyperparameters["eyeBinaryThreshold"] # 15

    ret, threshEye = cv2.threshold(forEye, eyeBinaryThreshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((self._hyperparameters["eyeFilterKernelSize"], self._hyperparameters["eyeFilterKernelSize"]), np.uint8)
    threshEye = cv2.erode(threshEye, kernel, iterations=1)
    threshEye = cv2.dilate(threshEye, kernel, iterations=1)

    threshEye[0,:] = 255
    threshEye[len(threshEye)-1,:] = 255
    threshEye[:,0] = 255
    threshEye[:,len(threshEye[0])-1] = 255

    contourLeft  = 0
    contourRight = 0

    contours, hierarchy = cv2.findContours(threshEye, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    maxLeft  = 1000000000000000000000000000
    maxRight = 1000000000000000000000000000
    maxArea  = len(threshEye) * len(threshEye[0]) * 0.9
    for contour in contours:
      area = cv2.contourArea(contour)
      M = cv2.moments(contour)
      if M['m00']:
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])
      else:
        cx = 0
        cy = 0
      if area < maxArea:
        if (leftEyeCoordinate[0] - cx)**2 + (leftEyeCoordinate[1] - cy)**2 < maxLeft:
          maxLeft  = (leftEyeCoordinate[0] - cx)**2 + (leftEyeCoordinate[1] - cy)**2
          contourLeft  = contour
        if (rightEyeCoordinate[0] - cx)**2 + (rightEyeCoordinate[1] - cy)**2 < maxRight:
          maxRight = (rightEyeCoordinate[0] - cx)**2 + (rightEyeCoordinate[1] - cy)**2
          contourRight = contour

    # Finding the (X, Y) coordinates and the angle of each of the two eyes
    eyeAngle = [0, 0]
    eyeX = [leftEyeCoordinate[0], rightEyeCoordinate[0]]
    eyeY = [leftEyeCoordinate[1], rightEyeCoordinate[1]]
    for idx, contour in enumerate([contourLeft, contourRight]):
      if type(contour) != int and len(contour) >= 3:
        if len(contour) >= 5:
          ellipse = cv2.fitEllipse(contour)
          angle1 = ellipse[2] * (math.pi / 180) + (math.pi / 2)
          if self._hyperparameters["debugEyeTrackingAdvanced"]:
            threshEye1 = np.zeros((len(threshEye), len(threshEye[0])))
            threshEye1[:, :] = 0
            threshEye1 = threshEye1.astype(np.uint8)
            cv2.fillPoly(threshEye1, pts =[contour], color=(255))
        else:
          print("problem with eye angle here, not enough points in the contour to use fitEllipse")
          threshEye1 = np.zeros((len(threshEye), len(threshEye[0])))
          threshEye1[:, :] = 0
          cv2.fillPoly(threshEye1, pts =[contour], color=(255))
          if self._hyperparameters["debugEyeTrackingAdvanced"]:
            self._debugFrame(threshEye1, title='Frame')

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

        headingApproximate = trackingHeadingAllAnimals[animalId, i-self._firstFrame] % (2*math.pi)
        headingPreciseOpt1 = angle1
        headingPreciseOpt2 = (angle1 + math.pi) % (2*math.pi)
        diffAngle1 = self._distBetweenThetas(headingApproximate, headingPreciseOpt1)
        diffAngle2 = self._distBetweenThetas(headingApproximate, headingPreciseOpt2)
        if (diffAngle1 < diffAngle2):
          eyeAngle[idx] = headingPreciseOpt1
        else:
          eyeAngle[idx] = headingPreciseOpt2
      else:
        eyeAngle[idx] = 0
    # Debugging Plot
    headingLineValidationPlotLength = self._hyperparameters["eyeTrackingHeadEmbeddedHalfDiameter"]
    if self._hyperparameters["debugEyeTracking"] or self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
      colorFrame = cv2.cvtColor(threshEye, cv2.COLOR_GRAY2RGB)
      cv2.circle(colorFrame, (eyeX[0], eyeY[0]), 2, (0,255,255), 1)
      cv2.line(colorFrame, (eyeX[0], eyeY[0]), (int(eyeX[0]+headingLineValidationPlotLength*math.cos(eyeAngle[0])), int(eyeY[0]+headingLineValidationPlotLength*math.sin(eyeAngle[0]))), (255,0,255), 1)
      cv2.line(colorFrame, (eyeX[1], eyeY[1]), (int(eyeX[1]+headingLineValidationPlotLength*math.cos(eyeAngle[1])), int(eyeY[1]+headingLineValidationPlotLength*math.sin(eyeAngle[1]))), (255,0,255), 1)
      cv2.circle(colorFrame, (eyeX[1], eyeY[1]), 2, (0,255,255), 1)
      if self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
        return self._adjustHeadEmbeddedEyeTrackingParamsEllipse(i, colorFrame, widgets)
      else:
        self._debugFrame(colorFrame, title='Eye Tracking debugging')

    # Storing the (X, Y) coordinates and angles
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 0] = leftEyeCoordinate[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 1] = leftEyeCoordinate[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 2] = eyeAngle[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 3] = 0
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 4] = rightEyeCoordinate[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 5] = rightEyeCoordinate[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 6] = eyeAngle[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 7] = 0

  def _eyeTracking(self, animalId, i, frame, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals):
    headCenterToMidEyesPointDistance   = self._hyperparameters["headCenterToMidEyesPointDistance"]
    eyeBinaryThreshold                 = self._hyperparameters["eyeBinaryThreshold"]
    midEyesPointToEyeCenterMaxDistance = self._hyperparameters["midEyesPointToEyeCenterMaxDistance"]
    eyeHeadingSearchAreaHalfDiameter   = self._hyperparameters["eyeHeadingSearchAreaHalfDiameter"]
    headingLineValidationPlotLength    = self._hyperparameters["headingLineValidationPlotLength"]
    debugEyeTracking                   = self._hyperparameters["debugEyeTracking"]
    debugEyeTrackingAdvanced           = self._hyperparameters["debugEyeTrackingAdvanced"]

    # Retrieving the X, Y coordinates of the center of the head of the fish and calculating the "mid eyes" point
    x = trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][0]
    y = trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][1]
    midEyesPointX = int(x+headCenterToMidEyesPointDistance*math.cos(trackingHeadingAllAnimals[animalId, i-self._firstFrame]))
    midEyesPointY = int(y+headCenterToMidEyesPointDistance*math.sin(trackingHeadingAllAnimals[animalId, i-self._firstFrame]))

    # Finding the connected components associated with each of the two eyes
    ret, threshEye = cv2.threshold(frame, eyeBinaryThreshold, 255, cv2.THRESH_BINARY)
    threshEye[0,:] = 255
    threshEye[len(threshEye)-1,:] = 255
    threshEye[:,0] = 255
    threshEye[:,len(threshEye[0])-1] = 255
    # Adding a white circle on the swim bladder
    whiteCircleDiameter = int(1.2 * headCenterToMidEyesPointDistance)
    whiteCircleX = int(x-whiteCircleDiameter*math.cos(trackingHeadingAllAnimals[animalId, i-self._firstFrame]))
    whiteCircleY = int(y-whiteCircleDiameter*math.sin(trackingHeadingAllAnimals[animalId, i-self._firstFrame]))
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
      self._debugFrame(threshEye, title='Frame')
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
    estimatedLeftEyeX = int(midEyesPointX + (distBetweenTheTwoEyes/2) * math.cos(trackingHeadingAllAnimals[animalId, i-self._firstFrame] - (math.pi/2)))
    estimatedLeftEyeY = int(midEyesPointY + (distBetweenTheTwoEyes/2) * math.sin(trackingHeadingAllAnimals[animalId, i-self._firstFrame] - (math.pi/2)))
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
            self._debugFrame(threshEye1, title='Frame')
          if False:
            angle1 = self._computeHeading(threshEye1, eyeX[idx], eyeY[idx], eyeHeadingSearchAreaHalfDiameter)
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

        headingApproximate = trackingHeadingAllAnimals[animalId, i-self._firstFrame] % (2*math.pi)
        headingPreciseOpt1 = angle1
        headingPreciseOpt2 = (angle1 + math.pi) % (2*math.pi)
        diffAngle1 = self._distBetweenThetas(headingApproximate, headingPreciseOpt1)
        diffAngle2 = self._distBetweenThetas(headingApproximate, headingPreciseOpt2)
        if (diffAngle1 < diffAngle2):
          eyeAngle[idx] = headingPreciseOpt1
        else:
          eyeAngle[idx] = headingPreciseOpt2
      else:
        eyeAngle[idx] = 0
    # Debugging Plot
    if debugEyeTracking:
      colorFrame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
      cv2.line(colorFrame, (int(x),int(y)), (int(x+2*headingLineValidationPlotLength*math.cos(trackingHeadingAllAnimals[animalId, i-self._firstFrame])), int(y+2*headingLineValidationPlotLength*math.sin(trackingHeadingAllAnimals[animalId, i-self._firstFrame]))), (255,0,0), 1)
      cv2.circle(colorFrame, (midEyesPointX, midEyesPointY), 2, (255,0,255), 1)
      cv2.circle(colorFrame, (eyeX[0], eyeY[0]), 2, (0,255,255), 1)
      cv2.line(colorFrame, (eyeX[0], eyeY[0]), (int(eyeX[0]+headingLineValidationPlotLength*math.cos(eyeAngle[0])), int(eyeY[0]+headingLineValidationPlotLength*math.sin(eyeAngle[0]))), (255,0,255), 1)
      cv2.line(colorFrame, (eyeX[1], eyeY[1]), (int(eyeX[1]+headingLineValidationPlotLength*math.cos(eyeAngle[1])), int(eyeY[1]+headingLineValidationPlotLength*math.sin(eyeAngle[1]))), (255,0,255), 1)
      cv2.circle(colorFrame, (eyeX[1], eyeY[1]), 2, (0,255,255), 1)
      self._debugFrame(colorFrame, title='Eye Tracking debugging')

    # Storing the (X, Y) coordinates and angles
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 0] = eyeX[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 1] = eyeY[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 2] = eyeAngle[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 3] = eyeArea[0]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 4] = eyeX[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 5] = eyeY[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 6] = eyeAngle[1]
    trackingEyesAllAnimals[animalId, i-self._firstFrame, 7] = eyeArea[1]

  def getAccentuateFrameForManualPointSelect(self, image):
    if self._hyperparameters["accentuateFrameForManualTailExtremityFind"]:
      frame = image.copy()
      quartileChose = 0.01
      lowVal  = int(np.quantile(frame, quartileChose))
      highVal = int(np.quantile(frame, 1 - quartileChose))
      frame[frame < lowVal]  = lowVal
      frame[frame > highVal] = highVal
      frame = frame - lowVal
      mult  = np.max(frame)
      frame = frame * (255/mult)
      frame = frame.astype(int)
      frame = (frame / np.linalg.norm(frame))*255
      return frame
    else:
      return image
