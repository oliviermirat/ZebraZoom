import math
import cv2
import numpy as np
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.calculateHeading import calculateHeadingSimple, calculateHeading

def multipleAnimalsHeadTracking(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, hyperparameters, gray, i, firstFrame, thresh1, thresh3):
  
  headCoordinatesOptions = []
  x = 0
  y = 0
  minAreaCur = hyperparameters["minArea"]
  maxAreaCur = hyperparameters["maxArea"]
  
  ret,thresh2 = cv2.threshold(gray,hyperparameters["thresholdForBlobImg"],255,cv2.THRESH_BINARY)
  erodeSize = hyperparameters["erodeSize"]
  kernel  = np.ones((erodeSize,erodeSize), np.uint8)
  thresh2 = cv2.dilate(thresh2, kernel, iterations=hyperparameters["dilateIter"])
  
  thresh2[:,0] = 255
  thresh2[0,:] = 255
  thresh2[:, len(thresh2[0])-1] = 255
  thresh2[len(thresh2)-1, :]    = 255
  
  if hyperparameters["multipleHeadTrackingIterativelyRelaxAreaCriteria"]:
    contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    while (len(headCoordinatesOptions) < hyperparameters["nbAnimalsPerWell"]) and (minAreaCur > 0):
      # print("MMMinAreaCur:", minAreaCur)
      for contour in contours:
        area = cv2.contourArea(contour)
        if (area > minAreaCur) and (area < maxAreaCur):
          # print("Find center of mass: area:", area)
          M = cv2.moments(contour)
          if M['m00']:
            x = int(M['m10']/M['m00'])
            y = int(M['m01']/M['m00'])
          else:
            x = 0
            y = 0
          if not([x, y] in headCoordinatesOptions):
            headCoordinatesOptions.append([x, y])
      
      if int(hyperparameters["minArea"]/10):
        minAreaCur = minAreaCur - int(hyperparameters["minArea"]/10)
        maxAreaCur = maxAreaCur + int(hyperparameters["minArea"]/10)
      else:
        minAreaCur = minAreaCur - 1
        maxAreaCur = maxAreaCur + 1   
  else:
    contours, hierarchy = cv2.findContours(thresh2,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
      area = cv2.contourArea(contour)
      if (area > minAreaCur) and (area < maxAreaCur):
        # print("Find center of mass: area:", area)
        M = cv2.moments(contour)
        if M['m00']:
          x = int(M['m10']/M['m00'])
          y = int(M['m01']/M['m00'])
        else:
          x = 0
          y = 0
        headCoordinatesOptions.append([x, y])

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
  
  for animal_Id in range(0, hyperparameters["nbAnimalsPerWell"]):
    x_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][0]
    y_curFrame_animal_Id  = trackingHeadTailAllAnimals[animal_Id, i-firstFrame][0][1]
    if x_curFrame_animal_Id != 0 and y_curFrame_animal_Id != 0:
      x_curFrame_animal_Id = int(x_curFrame_animal_Id)
      y_curFrame_animal_Id = int(y_curFrame_animal_Id)
      
      if hyperparameters["forceBlobMethodForHeadTracking"]: # Fish tracking, usually
        previousFrameHeading = trackingHeadingAllAnimals[animal_Id, i-firstFrame-1] if i-firstFrame-1 > 0 else 0
        [heading, lastFirstTheta] = calculateHeading(x_curFrame_animal_Id, y_curFrame_animal_Id, 0, thresh1, thresh2, 0, hyperparameters, previousFrameHeading)
      else: # Drosophilia, mouse, and other center of mass only tracking
        heading = calculateHeadingSimple(x_curFrame_animal_Id, y_curFrame_animal_Id, thresh2, hyperparameters)
      
      trackingHeadingAllAnimals[animal_Id, i-firstFrame] = heading
  
  return [trackingHeadingAllAnimals, trackingHeadTailAllAnimals]
