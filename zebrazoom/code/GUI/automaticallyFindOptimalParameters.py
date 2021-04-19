import numpy as np
import json
import cv2
import math
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
import cvui
import pickle
import json
import os
import re
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.findWells import findWells
from zebrazoom.code.trackingFolder.tracking import tracking
import pdb

def automaticallyFindOptimalParameters(self, controller, realExecThroughGUI):
  
  nbOfImagesToManuallyClassify = 3
  headAreaDividedByBodyAreaTarget = 0.4
  
  saveIntermediary = True # Should be set to True except when debugging
  # paraSetSaved (below) is the intermediary to reload when the boolean above is set to True
  # paraSetSaved = '4wellsZebrafishLarvaeEscapeResponses_paramSet'
  # paraSetSaved = 'Catamaran_10e_t2a_paramSet'
  paraSetSaved = 'maha_paramSet'
  
  # # # Getting ground truth from user: head center and tail extremity coordinates for a few frames
  
  if realExecThroughGUI:
    
    videoPath = self.videoToCreateConfigFileFor
    
    for m in re.finditer('/', videoPath):
      last = m.start()
      pathToVideo      = videoPath[:last+1]
      videoNameWithExt = videoPath[last+1:]
      allDotsPositions = [m.start() for m in re.finditer('\.', videoNameWithExt)]
      pointPos  = allDotsPositions[len(allDotsPositions)-1]
      videoName = videoNameWithExt[:pointPos]
      videoExt  = videoNameWithExt[pointPos+1:]
    
    initialConfigFile = self.configFile
    
    initialHyperparameters = getHyperparametersSimple(initialConfigFile)
    initialHyperparameters["videoName"]      = videoName
    wellPositions = findWells(os.path.join(pathToVideo, videoNameWithExt), initialHyperparameters)
    
    cap   = cv2.VideoCapture(videoPath)
    max_l = int(cap.get(7))
    
    # Finding the well with the most movement
    cap.set(1, 0)
    ret, firstFrame = cap.read()
    firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
    cap.set(1, max_l-1)
    ret, lastFrame = cap.read()
    lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
    pixelsChange = np.zeros((len(wellPositions)))
    for wellNumberId in range(0, len(wellPositions)):
      xtop  = wellPositions[wellNumberId]['topLeftX']
      ytop  = wellPositions[wellNumberId]['topLeftY']
      lenX  = wellPositions[wellNumberId]['lengthX']
      lenY  = wellPositions[wellNumberId]['lengthY']
      firstFrameROI = firstFrame[ytop:ytop+lenY, xtop:xtop+lenX]
      lastFrameROI  = lastFrame[ytop:ytop+lenY, xtop:xtop+lenX]
      pixelsChange[wellNumberId] = np.sum(abs(firstFrameROI-lastFrameROI))
    wellNumber = np.argmax(pixelsChange)
    
    backCalculationStep = int(max_l / nbOfImagesToManuallyClassify)
    data = []
    
    for k in range(0, max_l):
      
      if (k % backCalculationStep == 0):
        
        cap.set(1, k)
        ret, frame = cap.read()
        
        xtop  = wellPositions[wellNumber]['topLeftX']
        ytop  = wellPositions[wellNumber]['topLeftY']
        lenX  = wellPositions[wellNumber]['lengthX']
        lenY  = wellPositions[wellNumber]['lengthY']
        frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]
        
        WINDOW_NAME_1 = "Click on the center of the head of one animal"
        cvui.init(WINDOW_NAME_1)
        cv2.moveWindow(WINDOW_NAME_1, 0,0)
        cvui.imshow(WINDOW_NAME_1, frame)
        while not(cvui.mouse(cvui.CLICK)):
          cursor = cvui.mouse()
          if cv2.waitKey(20) == 27:
            break
          headCoordinates = [cursor.x, cursor.y]
        cv2.destroyAllWindows()
        
        WINDOW_NAME_2 = "Click on the tip of the tail of the same animal"
        cvui.init(WINDOW_NAME_2)
        cv2.moveWindow(WINDOW_NAME_2, 0,0)
        frame2 = frame.copy()
        frame2 = cv2.circle(frame, (headCoordinates[0], headCoordinates[1]), 2, (0, 0, 255), -1)
        cvui.imshow(WINDOW_NAME_2, frame2)
        while not(cvui.mouse(cvui.CLICK)):
          cursor = cvui.mouse()
          if cv2.waitKey(20) == 27:
            break
          tailTipCoordinates = [cursor.x, cursor.y]
        frame2 = cv2.circle(frame, (tailTipCoordinates[0], tailTipCoordinates[1]), 2, (0, 0, 255), -1)  
        cvui.imshow(WINDOW_NAME_2, frame2)
        cv2.waitKey(2000)
        cv2.destroyAllWindows()
        
        if False: # Centered on the animal
          minX = min(headCoordinates[0], tailTipCoordinates[0])
          maxX = max(headCoordinates[0], tailTipCoordinates[0])
          minY = min(headCoordinates[1], tailTipCoordinates[1])
          maxY = max(headCoordinates[1], tailTipCoordinates[1])
          lengthX = maxX - minX
          lengthY = maxY - minY
          
          widdeningFactor = 2
          minX = minX - int(widdeningFactor * lengthX)
          maxX = maxX + int(widdeningFactor * lengthX)
          minY = minY - int(widdeningFactor * lengthY)
          maxY = maxY + int(widdeningFactor * lengthY)
          
          oneWellManuallyChosenTopLeft     = [minX, minY]
          oneWellManuallyChosenBottomRight = [maxX, maxY]
        else: # Focused on the initial well
          oneWellManuallyChosenTopLeft     = [xtop, ytop]
          oneWellManuallyChosenBottomRight = [xtop + lenX, ytop + lenY]          
        
        data.append({"image": frame, "headCoordinates": headCoordinates, "tailTipCoordinates": tailTipCoordinates, "oneWellManuallyChosenTopLeft": oneWellManuallyChosenTopLeft, "oneWellManuallyChosenBottomRight": oneWellManuallyChosenBottomRight, "frameNumber": k, "wellNumber": wellNumber})
  
    if saveIntermediary:
      toSave    = [initialConfigFile, videoPath, data, wellPositions, pathToVideo, videoNameWithExt, videoName, videoExt]
      pickle.dump(toSave, open(videoName + '_paramSet', 'wb'))
      
  else:
    
    toSave = pickle.load(open(paraSetSaved, 'rb'))
    initialConfigFile = toSave[0]
    videoPath         = toSave[1]
    data              = toSave[2]
    wellPositions     = toSave[3]
    pathToVideo       = toSave[4]
    videoNameWithExt  = toSave[5]
    videoName         = toSave[6]
    videoExt          = toSave[7]
    
    # data2 = []
    # data2.append(data[0])
    # data2.append(data[1])
    # data = data2
  
  print("initialConfigFile:", initialConfigFile)
  
  # # # Starting the process of finding the best hyperparameters to track the video
  
  configFile = {"extractAdvanceZebraParameters": 0, "headEmbeded": 0, "nbWells": 1, "noBoutsDetection": 1, "noChecksForBoutSelectionInExtractParams": 1, "trackingPointSizeDisplay": 4, "validationVideoPlotHeading": 1, "nbAnimalsPerWell": initialConfigFile["nbAnimalsPerWell"], "forceBlobMethodForHeadTracking": 1, "multipleHeadTrackingIterativelyRelaxAreaCriteria": 1, "erodeIter":0, "minArea": 0, "maxArea": 100000000000000, "minAreaBody": 0, "maxAreaBody": 100000000000000, "headSize": 20, "minTailSize": 0, "maxTailSize": 100000000000000, "paramGaussianBlur": 25, "extractBackWhiteBackground": 1, "dilateIter": 1, "thresholdForBlobImg": 254, "findContourPrecision": "CHAIN_APPROX_NONE", "midlineIsInBlobTrackingOptimization": 0}
  
  hyperparameters = getHyperparametersSimple(configFile)
  
  background = getBackground(os.path.join(pathToVideo, videoNameWithExt), hyperparameters)
  
  hyperparameters["minPixelDiffForBackExtract"] = 20
  
  # # # For each frame that has some ground truth provided by the user:
  # # # Finds the parameter minPixelDiffForBackExtract (as well as the corresponding number of black pixels in the black frame) that leads to a tail extremity detected as close as possible to the tail extremity value provided by the user
  
  for image in data:
    
    oneWellManuallyChosenTopLeft     = image["oneWellManuallyChosenTopLeft"]
    oneWellManuallyChosenBottomRight = image["oneWellManuallyChosenBottomRight"]
    
    hyperparameters["oneWellManuallyChosenTopLeft"]     = oneWellManuallyChosenTopLeft
    hyperparameters["oneWellManuallyChosenBottomRight"] = oneWellManuallyChosenBottomRight
    hyperparameters["videoWidth"]    = oneWellManuallyChosenBottomRight[0] - oneWellManuallyChosenTopLeft[0]
    hyperparameters["videoHeight"]   = oneWellManuallyChosenBottomRight[1] - oneWellManuallyChosenTopLeft[1]
    
    hyperparameters["firstFrame"]    = image["frameNumber"]
    hyperparameters["lastFrame"]     = image["frameNumber"]
    hyperparameters["debugTracking"] = 0
    
    hyperparameters["fixedHeadPositionX"] = int(image["headCoordinates"][0])
    hyperparameters["fixedHeadPositionY"] = int(image["headCoordinates"][1])
    hyperparameters["midlineIsInBlobTrackingOptimization"] = 0
    
    bestMinPixelDiffForBackExtract = 10
    lowestTailTipDistError = 1000000000
    for minPixelDiffForBackExtract in range(3, 25):
      print("trying with minPixelDiffForBackExtract:", minPixelDiffForBackExtract)
      hyperparameters["minPixelDiffForBackExtract"] = minPixelDiffForBackExtract
      trackingData = tracking(videoPath, background, image["wellNumber"], wellPositions, hyperparameters, videoName)
      tailTipGroundTruth = image["tailTipCoordinates"] #[image["tailTipCoordinates"][0] - image["oneWellManuallyChosenTopLeft"][0], image["tailTipCoordinates"][1] - image["oneWellManuallyChosenTopLeft"][1]]
      tailTipPredicted = trackingData[0][0][0][len(trackingData[0][0][0])-1]
      if (trackingData[0][0][0][0][0] == tailTipPredicted[0] and trackingData[0][0][0][0][1] == tailTipPredicted[1]) or (trackingData[0][0][0][1][0] == tailTipPredicted[0] and trackingData[0][0][0][1][1] == tailTipPredicted[1]):
        tailTipDistError = 1000000000
      else:
        tailTipDistError = math.sqrt((tailTipGroundTruth[0] - tailTipPredicted[0])** 2 + (tailTipGroundTruth[1] - tailTipPredicted[1])**2)
      if tailTipDistError < lowestTailTipDistError:
        lowestTailTipDistError = tailTipDistError
        bestMinPixelDiffForBackExtract = minPixelDiffForBackExtract
        previousDataPoint = []
        tailLength = 0
        for dataPoint in trackingData[0][0][0]:
          if len(previousDataPoint):
            tailLength = tailLength + math.sqrt((dataPoint[0] - previousDataPoint[0])**2 + (dataPoint[1] - previousDataPoint[1])**2)
          previousDataPoint = dataPoint
        image["tailLength"] = tailLength
        image["tailLengthManual"] = math.sqrt((image["headCoordinates"][0] - tailTipGroundTruth[0])**2 + (image["headCoordinates"][1] - tailTipGroundTruth[1])**2)
    
    image["bestMinPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
    image["lowestTailTipDistError"]         = lowestTailTipDistError
    
    if lowestTailTipDistError != 1000000000:
      hyperparameters["minPixelDiffForBackExtract"] = image["bestMinPixelDiffForBackExtract"]
      [foregroundImage, o1, o2] = getForegroundImage(videoPath, background, image["frameNumber"], image["wellNumber"], wellPositions, hyperparameters)
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      contourClickedByUser = 0
      contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (image["headCoordinates"][0], image["headCoordinates"][1]), True)
        if dist >= 0:
          contourClickedByUser = contour
      if not(type(contourClickedByUser) == int): # We found the contour that the user selected
        bodyContourArea = cv2.contourArea(contourClickedByUser)
        image["bodyContourArea"] = bodyContourArea
      else:
        image["bodyContourArea"] = -1
      
    del hyperparameters["fixedHeadPositionX"]
    del hyperparameters["fixedHeadPositionY"]
    del hyperparameters["midlineIsInBlobTrackingOptimization"]
    
  # # # Choosing the hyperparameters related to the background substraction and to the tail length as well as the headSize hyperparameter (for the heading calculation)
  
  tailLengthManualOptions = []
  for image in data:
    tailLengthManualOptions.append(image["tailLengthManual"])
  maxTailLengthManual = max(tailLengthManualOptions)
  print("tailLengthManualOptions:", tailLengthManualOptions)
  print("maxTailLengthManual:", maxTailLengthManual)
  
  bestMinPixelDiffForBackExtract = -1
  bestMinPixelDiffForBackExtractOptions = []
  bodyContourAreaOptions = []
  tailLengthOptions = []
  for image in data:
    if image["lowestTailTipDistError"] != 1000000000 and (image["tailLength"] < 10 * maxTailLengthManual):
      bestMinPixelDiffForBackExtractOptions.append(image["bestMinPixelDiffForBackExtract"])
      tailLengthOptions.append(image["tailLength"])
      if image["bodyContourArea"] != -1:
        bodyContourAreaOptions.append(image["bodyContourArea"])
  
  if len(bestMinPixelDiffForBackExtractOptions):
    bestMinPixelDiffForBackExtract = np.mean(bestMinPixelDiffForBackExtractOptions)
    tailLength = np.mean(tailLengthOptions)
  
  if len(bodyContourAreaOptions):
    bodyContourArea = np.mean(bodyContourAreaOptions)
  else:
    print("NEED TO START OVER: bodyContourArea")
    bodyContourArea = 0
  
  if bestMinPixelDiffForBackExtract == -1:
    print("NEED TO START OVER")
    
  print("bestMinPixelDiffForBackExtractOptions:", bestMinPixelDiffForBackExtractOptions)
  print("tailLengthOptions:", tailLengthOptions)
  print("bodyContourAreaOptions:", bodyContourAreaOptions)
  
  hyperparameters["minPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
  hyperparameters["minTailSize"] = tailLength / 10
  hyperparameters["maxTailSize"] = tailLength * 2
  hyperparameters["headSize"]    = int(tailLength / 2)
  configFile["minPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
  configFile["minTailSize"] = tailLength / 10
  configFile["maxTailSize"] = tailLength * 2
  configFile["headSize"]    = int(tailLength / 2)
  
  hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = bodyContourArea * configFile["nbAnimalsPerWell"]
  configFile["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = bodyContourArea * configFile["nbAnimalsPerWell"]
  
  # # # For each frame that has some ground truth provided by the user:
  # # # Finds the area of the body as well as the optimal dilateIter hyperparameters to go from body contour to head contour
  
  for image in data:
    
    if image["lowestTailTipDistError"] != 1000000000 and image["bodyContourArea"] and (image["tailLength"] < 10 * maxTailLengthManual):
      
      bodyContourArea = image["bodyContourArea"]
      
      [foregroundImage, o1, o2] = getForegroundImage(videoPath, background, image["frameNumber"], image["wellNumber"], wellPositions, hyperparameters)
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)

      contourClickedByUser = 0
      contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (image["headCoordinates"][0], image["headCoordinates"][1]), True)
        if dist >= 0:
          contourClickedByUser = contour
      
      if not(type(contourClickedByUser) == int): # We found the contour that the user selected
        image["contourClickedByUser"] = contourClickedByUser
        thresh2 = thresh.copy()
        erodeSize = hyperparameters["erodeSize"]
        kernel  = np.ones((erodeSize, erodeSize), np.uint8)
        
        curHeadAreaDividedByBodyArea = 1.1
        dilateIter = 0
        while curHeadAreaDividedByBodyArea > headAreaDividedByBodyAreaTarget:
          dilateIter = dilateIter + 1
          thresh2_b = cv2.dilate(thresh2, kernel, iterations=dilateIter)
          contours, hierarchy = cv2.findContours(thresh2_b, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
          correspondingHeadContour = 0
          maxDist    = 100000000
          for contour in contours:
            M = cv2.moments(contour)
            if M['m00']:
              x = int(M['m10']/M['m00'])
              y = int(M['m01']/M['m00'])
            else:
              x = 0
              y = 0
            dist = cv2.pointPolygonTest(contourClickedByUser, (x, y), True)
            if dist >= 0:
              dist = math.sqrt((image["headCoordinates"][0] - x)**2 + (image["headCoordinates"][1] - y)**2)
              if dist < maxDist:
                maxDist = dist
                correspondingHeadContour = contour
          if not(type(correspondingHeadContour) == int):
            headContourArea = cv2.contourArea(correspondingHeadContour)
            curHeadAreaDividedByBodyArea = headContourArea / bodyContourArea
            print("curHeadAreaDividedByBodyArea, headContourArea, bodyContourArea, dilateIter:", curHeadAreaDividedByBodyArea, headContourArea, bodyContourArea, dilateIter)
          else:
            curHeadAreaDividedByBodyArea = 0
        if curHeadAreaDividedByBodyArea == 0:
          dilateIter = dilateIter - 1
        image["dilateIter"] = dilateIter
  
  # # # Choosing the hyperparameters related to the max and min of the body contour as well as the dilateIter hyperparameters to go from body contour to head contour
  
  dilateIterOptions = []
  for image in data:
    if image["lowestTailTipDistError"] != 1000000000 and (image["tailLength"] < 10 * maxTailLengthManual):
      dilateIterOptions.append(image["dilateIter"])
      
  print("dilateIterOptions:", dilateIterOptions)
  
  if len(dilateIterOptions):
    hyperparameters["dilateIter"] = int(np.ceil(np.median(dilateIterOptions)))
    configFile["dilateIter"] = int(np.ceil(np.median(dilateIterOptions)))
  else:
    print("NEED TO START OVER FOR dilateIter")
  
  # # # For each frame that has some ground truth provided by the user:
  # # # Finds the area of the head
  
  for image in data:
  
    if image["lowestTailTipDistError"] != 1000000000 and (image["tailLength"] < 10 * maxTailLengthManual):
    
      [foregroundImage, o1, o2] = getForegroundImage(videoPath, background, image["frameNumber"], image["wellNumber"], wellPositions, hyperparameters)
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      
      contourClickedByUser = image["contourClickedByUser"]
      
      thresh2 = cv2.dilate(thresh, kernel, iterations=hyperparameters["dilateIter"])
      contours, hierarchy = cv2.findContours(thresh2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      correspondingHeadContour = 0
      maxDist    = 100000000
      for contour in contours:
        M = cv2.moments(contour)
        if M['m00']:
          x = int(M['m10']/M['m00'])
          y = int(M['m01']/M['m00'])
        else:
          x = 0
          y = 0
        dist = cv2.pointPolygonTest(contourClickedByUser, (x, y), True)
        if dist >= 0:
          dist = math.sqrt((image["headCoordinates"][0] - x)**2 + (image["headCoordinates"][1] - y)**2)
          if dist < maxDist:
            maxDist = dist
            correspondingHeadContour = contour
      
      if not(type(correspondingHeadContour) == int):
        headContourArea = cv2.contourArea(correspondingHeadContour)
        image["headContourArea"] = headContourArea
  
  # # # Choosing the hyperparameters related to the max and min of the head contour
  
  headContourAreaOptions = []
  for image in data:
    if image["lowestTailTipDistError"] != 1000000000 and (image["tailLength"] < 10 * maxTailLengthManual):
      if "headContourArea" in image:
        headContourAreaOptions.append(image["headContourArea"])
  print("headContourAreaOptions:", headContourAreaOptions)
  if len(headContourAreaOptions):
    headContourArea = np.mean(headContourAreaOptions)
  else:
    print("Start Over!!!")
  hyperparameters["minArea"] = 0.7 * headContourArea
  hyperparameters["maxArea"] = 1.3 * headContourArea
  configFile["minArea"] = 0.7 * headContourArea
  configFile["maxArea"] = 1.3 * headContourArea
  
  # # # Overwritting some of the hyperparameters from hyperparameters in the initial configFile
  
  listOfParametersToOverwrite = ["nbWells", "nbRowsOfWells", "nbWellsPerRows", "minWellDistanceForWellDetection", "wellOutputVideoDiameter", "wellsAreRectangles", "rectangleWellAreaImageThreshold", "rectangleWellErodeDilateKernelSize", "findRectangleWellArea", "rectangularWellsInvertBlackWhite", "noWellDetection"]
  for parameter in listOfParametersToOverwrite:
    if parameter in initialConfigFile:
      configFile[parameter] = initialConfigFile[parameter]
  configFile["recalculateForegroundImageBasedOnBodyArea"] = 1
      
  # # # Moving on to the next step
  
  if realExecThroughGUI:
    self.configFile = configFile
    # Need to do a redirect here
  
  print("final Config File", configFile)
  
  reference = videoName + '_config.json'
  with open(reference, 'w') as outfile:
    json.dump(configFile, outfile)
  
  