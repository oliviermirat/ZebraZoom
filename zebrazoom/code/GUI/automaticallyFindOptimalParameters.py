import numpy as np
import json
import math
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.mainZZ import mainZZ
import pickle
import json
import os
import re

import zebrazoom.code.util as util
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.findWells import findWells
from zebrazoom.code.trackingFolder.tracking import tracking

from zebrazoom.code.GUI.adjustParameterInsideAlgo import adjustBoutDetectionOnlyPage
from zebrazoom.code.GUI.automaticallyFindOptimalParametersFunctions import getGroundTruthFromUser, findBestBackgroundSubstractionParameterForEachImage, findInitialBlobArea, boutDetectionParameters


@util.showInProgressPage('Calculation')
def _automaticallyFindOptimalParameters(self, controller, realExecThroughGUI, detectBoutsMethod, method, nbOfAnimalToTrackNotConstantOverTime, adjustBackgroundExtractionBasedOnNumberOfBlackPixels, groundTruth, zebrafishToTrack):
  if realExecThroughGUI:
    [initialConfigFile, videoPath, data, wellPositions, pathToVideo, videoNameWithExt, videoName, videoExt] = groundTruth
  else:
    toSave = pickle.load(open(self, 'rb'))
    initialConfigFile = toSave[0]
    videoPath         = toSave[1]
    data              = toSave[2]
    wellPositions     = toSave[3]
    pathToVideo       = toSave[4]
    videoNameWithExt  = toSave[5]
    videoName         = toSave[6]
    videoExt          = toSave[7]
    zebrafishToTrack  = toSave[8]

  print("initialConfigFile:", initialConfigFile)

  # # # Starting the process of finding the best hyperparameters to track the video
  
  if zebrafishToTrack:
    configFile = {"extractAdvanceZebraParameters": 0, "headEmbeded": 0, "nbWells": 1, "noBoutsDetection": 1, "noChecksForBoutSelectionInExtractParams": 1, "trackingPointSizeDisplay": 4, "validationVideoPlotHeading": 1, "nbAnimalsPerWell": 1, "forceBlobMethodForHeadTracking": 1, "multipleHeadTrackingIterativelyRelaxAreaCriteria": 1, "erodeIter":0, "minArea": 0, "maxArea": 100000000000000, "minAreaBody": 0, "maxAreaBody": 100000000000000, "headSize": 20, "minTailSize": 0, "maxTailSize": 100000000000000, "paramGaussianBlur": 25, "extractBackWhiteBackground": 1, "dilateIter": 0, "thresholdForBlobImg": 254, "findContourPrecision": "CHAIN_APPROX_NONE", "midlineIsInBlobTrackingOptimization": 0, "checkAllContourForTailExtremityDetect": 1, "recalculateForegroundImageBasedOnBodyArea": 0, "headingCalculationMethod": "simplyFromPreviousCalculations", "detectMouthInsteadOfHeadTwoSides": 1, "findCenterOfAnimalByIterativelyDilating": 1}
  else:
    configFile = {"nbWells": 1, "noBoutsDetection": 1, "trackingPointSizeDisplay": 4, "validationVideoPlotHeading": 0, "nbAnimalsPerWell": 1, "forceBlobMethodForHeadTracking": 1, "multipleHeadTrackingIterativelyRelaxAreaCriteria": 1, "erodeIter":0, "minArea": 0, "maxArea": 100000000000000, "minAreaBody": 0, "maxAreaBody": 100000000000000, "headSize": 20, "minTailSize": 0, "maxTailSize": 100000000000000, "paramGaussianBlur": 25, "extractBackWhiteBackground": 1, "dilateIter": 0, "thresholdForBlobImg": 254, "findContourPrecision": "CHAIN_APPROX_NONE", "recalculateForegroundImageBasedOnBodyArea": 0, "headingCalculationMethod": "simplyFromPreviousCalculations", "trackTail": 0}
  
  if "trackingMethod" in initialConfigFile:
    configFile["trackingMethod"] = initialConfigFile["trackingMethod"]
  
  originalConfigFile = self.configFile
  paramsToOverwriteFromOriginalConfigFile = ["setBackgroundToImageMedian"]
  for param in paramsToOverwriteFromOriginalConfigFile:
    if param in originalConfigFile:
      configFile[param] = originalConfigFile[param]
  
  if "firstFrame" in initialConfigFile:
    configFile["firstFrame"] = initialConfigFile["firstFrame"]
  if "lastFrame" in initialConfigFile:
    configFile["lastFrame"]  = initialConfigFile["lastFrame"]
  
  hyperparameters = getHyperparametersSimple(configFile)
  
  background = getBackground(os.path.join(pathToVideo, videoNameWithExt), hyperparameters)
  
  hyperparameters["minPixelDiffForBackExtract"] = 20
  
  # # # For each frame that has some ground truth provided by the user:
  # # # Finds the parameter minPixelDiffForBackExtract (as well as the corresponding number of black pixels in the black frame) that leads to a tail extremity detected as close as possible to the tail extremity value provided by the user
  
  data = findBestBackgroundSubstractionParameterForEachImage(data, videoPath, background, wellPositions, hyperparameters, videoName, zebrafishToTrack)
  
  # # # Choosing the hyperparameters related to the background substraction and to the tail length as well as the headSize hyperparameter (for the heading calculation)
  
  configFile["nbAnimalsPerWell"]      = initialConfigFile["nbAnimalsPerWell"]
  hyperparameters["nbAnimalsPerWell"] = initialConfigFile["nbAnimalsPerWell"]
  
  maxTailLengthManual = 100000000000
  if zebrafishToTrack:
    tailLengthManualOptions = []
    for image in data:
      tailLengthManualOptions.append(image["tailLengthManual"])
    maxTailLengthManual = max(tailLengthManualOptions)
    print("tailLengthManualOptions:", tailLengthManualOptions)
    print("maxTailLengthManual:", maxTailLengthManual)
  
  bestMinPixelDiffForBackExtract = -1
  bestMinPixelDiffForBackExtractOptions = []
  bodyContourAreaOptions = []
  lowestTailTipDistErrorOptions = []
  tailLengthOptions = []
  for image in data:
    if image["lowestTailTipDistError"] != 1000000000 and (not("tailLength" in image) or (image["tailLength"] < 10 * maxTailLengthManual)):
      if image["bodyContourArea"] != -1:
        bestMinPixelDiffForBackExtractOptions.append(image["bestMinPixelDiffForBackExtract"])
        bodyContourAreaOptions.append(image["bodyContourArea"])
        lowestTailTipDistErrorOptions.append(image["lowestTailTipDistError"])
        if zebrafishToTrack:
          tailLengthOptions.append(image["tailLength"])
  
  print("bestMinPixelDiffForBackExtractOptions:", bestMinPixelDiffForBackExtractOptions)
  print("tailLengthOptions:", tailLengthOptions)
  print("bodyContourAreaOptions:", bodyContourAreaOptions)
  
  if len(bestMinPixelDiffForBackExtractOptions):
    if adjustBackgroundExtractionBasedOnNumberOfBlackPixels:
      ind = np.argmin(bodyContourAreaOptions)
    else:
      ind = np.argmin(lowestTailTipDistErrorOptions)
    bestMinPixelDiffForBackExtract = bestMinPixelDiffForBackExtractOptions[ind] # THIS IS THE MOST IMPORTANT PART
    bodyContourArea = bodyContourAreaOptions[ind]
    if zebrafishToTrack:
      tailLength = tailLengthOptions[ind]
  else:
    print("NEED TO START OVER: bodyContourArea")
    bodyContourArea = 0
  if bestMinPixelDiffForBackExtract == -1:
    print("NEED TO START OVER")
  
  hyperparameters["minPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
  if nbOfAnimalToTrackNotConstantOverTime:
    hyperparameters["multipleHeadTrackingIterativelyRelaxAreaCriteria"] = 0
  else:
    if adjustBackgroundExtractionBasedOnNumberOfBlackPixels:
      hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = bodyContourArea * configFile["nbAnimalsPerWell"]
  hyperparameters["maxAreaBody"] = 5 * bodyContourArea
  hyperparameters["minAreaBody"] = int(bodyContourArea / 5)
  hyperparameters["trackingPointSizeDisplay"] = int(np.ceil(math.sqrt(bodyContourArea) / 15))
  if zebrafishToTrack:
    hyperparameters["minTailSize"] = tailLength / 10
    hyperparameters["maxTailSize"] = tailLength * 2
    hyperparameters["headSize"]    = int(tailLength / 2)
  
  configFile["minPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
  if nbOfAnimalToTrackNotConstantOverTime:
    configFile["multipleHeadTrackingIterativelyRelaxAreaCriteria"] = 0
  else:
    if adjustBackgroundExtractionBasedOnNumberOfBlackPixels:
      configFile["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = bodyContourArea * configFile["nbAnimalsPerWell"]
  configFile["maxAreaBody"] = 5 * bodyContourArea
  configFile["minAreaBody"] = int(bodyContourArea / 5)
  configFile["trackingPointSizeDisplay"] = int(np.ceil(math.sqrt(bodyContourArea) / 15))
  if zebrafishToTrack:
    configFile["minTailSize"] = tailLength / 10
    configFile["maxTailSize"] = tailLength * 2
    configFile["headSize"]    = int(tailLength / 2)
  
  # # # For each frame that has some ground truth provided by the user: finds the contour clicked by the user and its area USING THE NEW CONFIG FILE PARAMETERS SET JUST ABOVE
  
  data = findInitialBlobArea(data, videoPath, background, wellPositions, hyperparameters, maxTailLengthManual)
  
  # # # Choosing the hyperparameters related to the max and min of the "head" contour (the initial contours found during the tracking)
  
  headContourAreaOptions = []
  for image in data:
    if image["lowestTailTipDistError"] != 1000000000 and (not("tailLength" in image) or (image["tailLength"] < 10 * maxTailLengthManual)):
      if "headContourArea" in image:
        headContourAreaOptions.append(image["headContourArea"])
  print("headContourAreaOptions:", headContourAreaOptions)
  if len(headContourAreaOptions):
    headContourArea = np.mean(headContourAreaOptions)
  else:
    print("Start Over!!!")
  if nbOfAnimalToTrackNotConstantOverTime:
    hyperparameters["minArea"] = 0.5 * headContourArea
    hyperparameters["maxArea"] = 1.5 * headContourArea
    configFile["minArea"] = 0.5 * headContourArea
    configFile["maxArea"] = 1.5 * headContourArea  
  else:
    hyperparameters["minArea"] = 0.7 * headContourArea
    hyperparameters["maxArea"] = 1.3 * headContourArea
    configFile["minArea"] = 0.7 * headContourArea
    configFile["maxArea"] = 1.3 * headContourArea
    
  if not((0 < configFile["minAreaBody"]) and (configFile["minAreaBody"] < configFile["minArea"]) and (configFile["minArea"] < configFile["maxArea"]) and (configFile["maxArea"] < configFile["maxAreaBody"])):
    configFile["minArea"] = configFile["minAreaBody"]
    configFile["maxArea"] = configFile["maxAreaBody"]
  
  hyperparameters["dilateIter"] = 0
  configFile["dilateIter"] = 0
  
  # # # Overwritting some of the hyperparameters from hyperparameters in the initial configFile
  
  listOfParametersToOverwrite = ["extractAdvanceZebraParameters", "nbWells", "nbRowsOfWells", "nbWellsPerRows", "minWellDistanceForWellDetection", "wellOutputVideoDiameter", "wellsAreRectangles", "rectangleWellAreaImageThreshold", "rectangleWellErodeDilateKernelSize", "findRectangleWellArea", "rectangularWellsInvertBlackWhite", "noWellDetection", "oneWellManuallyChosenTopLeft", "oneWellManuallyChosenBottomRight", "multipleROIsDefinedDuringExecution", "groupOfMultipleSameSizeAndShapeEquallySpacedWells"]
  for parameter in listOfParametersToOverwrite:
    if parameter in initialConfigFile:
      configFile[parameter] = initialConfigFile[parameter]
  
  print("Intermediary config file:", configFile)
    
  # Adjusting config file hyperparameters related to bouts detection
  if detectBoutsMethod == 1:
    configFile = boutDetectionParameters(data, configFile, pathToVideo, videoName, videoExt, wellPositions, videoPath)

  # Setting recalculateForegroundImageBasedOnBodyArea to 1 when asked by user to try to obtain better tail tracking
  if adjustBackgroundExtractionBasedOnNumberOfBlackPixels and method:
    configFile["recalculateForegroundImageBasedOnBodyArea"] = 1
  
  # # # Moving on to the next step
  
  if realExecThroughGUI:
    self.configFile = configFile
    if detectBoutsMethod == 2:
      from PyQt5.QtCore import QEventLoop
      configFile["coordinatesOnlyBoutDetection"] = 1
      configFile["noBoutsDetection"] = 0
      loop = QEventLoop()
      util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, boutDetectionsOnly=True, nextCb=loop.exit, reloadWellPositions=True)
      loop.exec()
    util.addToHistory(controller.show_frame)("FinishConfig")
  else:  
    reference = videoName + '_config.json'
    with open(reference, 'w') as outfile:
      json.dump(configFile, outfile)
  
  print("final Config File", configFile)


def automaticallyFindOptimalParameters(self, controller, realExecThroughGUI, detectBoutsMethod, method, nbOfAnimalToTrackNotConstantOverTime, adjustBackgroundExtractionBasedOnNumberOfBlackPixels):

  nbOfImagesToManuallyClassify = 3
  saveIntermediary = False # Should be set to False except when debugging
  zebrafishToTrack = True

  # # # Getting ground truth from user: head center and tail extremity coordinates for a few frames

  if realExecThroughGUI:
    zebrafishToTrack = (self.organism == 'zebrafishNew')
    groundTruth = getGroundTruthFromUser(self, controller, nbOfImagesToManuallyClassify, saveIntermediary, zebrafishToTrack)
    if groundTruth is None:
      return
  else:
    groundTruth = None

  _automaticallyFindOptimalParameters(self, controller, realExecThroughGUI, detectBoutsMethod, method, nbOfAnimalToTrackNotConstantOverTime, adjustBackgroundExtractionBasedOnNumberOfBlackPixels, groundTruth, zebrafishToTrack)
