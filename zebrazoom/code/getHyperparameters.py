from pathlib import Path
import json
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import os
import zebrazoom.code.paths as paths
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

cur_dir_path = os.path.dirname(os.path.realpath(__file__))

cur_dir_path2 = Path(cur_dir_path)
cur_dir_path2 = cur_dir_path2.parent

with open(os.path.join(cur_dir_path, 'defaultConfigFile.json')) as f:
  configDefault = json.load(f)

# Returns parameters in config file
def getConfig(config, variableName, videoPath):
  
  if variableName in config:
    
    return config[variableName]
    
  else:
    
    if variableName in configDefault:
      
      if variableName == "outputFolder":
        return paths.getDefaultZZoutputFolder()
      else:
        return configDefault[variableName]
        
    else:
      
      cap = 0
      if len(videoPath):
        cap = zzVideoReading.VideoCapture(videoPath)
      if (len(videoPath) == 0) or (cap.isOpened() == False):
        print("Error opening video stream or file in getConfig")
        if variableName == "firstFrame":
          return 1
        else:
          return 0
      else:
        if variableName == "firstFrame":
          return 1
        elif variableName == "lastFrame":
          lastFrame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
          return lastFrame
        elif variableName == "videoWidth":
          frame_width  = int(cap.get(3))
          return frame_width
        elif variableName == "videoHeight":
          frame_height = int(cap.get(4))
          return frame_height
        else:
          print("You need to put the parameter",variableName,"in your configuration file")
          return 0

def getHyperparameters(configFile, videoName, videoPath, argv):

  hyperparameters = {}
  
  if type(configFile) == str:
    with open(configFile) as f:
      config = json.load(f)
  else:
    config = configFile
    
  if "parentConfigFiles" in config:
    for parentConfigFile in config["parentConfigFiles"]:
      with open(os.path.join(cur_dir_path2, parentConfigFile)) as f2:
        parentConfig = json.load(f2)
        parentConfig.update(config)
        config = parentConfig
  
  hyperparameters["minWellDistanceForWellDetection"] = getConfig(config, "minWellDistanceForWellDetection", videoPath)
  hyperparameters["wellOutputVideoDiameter"] = getConfig(config, "wellOutputVideoDiameter", videoPath)
  hyperparameters["firstFrame"] = getConfig(config, "firstFrame", videoPath)
  hyperparameters["lastFrame"] = getConfig(config, "lastFrame", videoPath)
  hyperparameters["nbWells"] = getConfig(config, "nbWells", videoPath)
  hyperparameters["backCalculationStep"] = getConfig(config, "backCalculationStep", videoPath)
  hyperparameters["onlyTrackThisOneWell"] = getConfig(config, "onlyTrackThisOneWell", videoPath)
  hyperparameters["thresAngleBoutDetect"] = getConfig(config, "thresAngleBoutDetect", videoPath)
  # Getting parameters more specifically related to the tracking
  hyperparameters["step"] = getConfig(config, "step", videoPath)
  hyperparameters["nbList"] = getConfig(config, "nbList", videoPath)
  hyperparameters["expDecreaseFactor"] = getConfig(config, "expDecreaseFactor", videoPath)
  hyperparameters["minArea"] = getConfig(config, "minArea", videoPath)
  hyperparameters["maxArea"] = getConfig(config, "maxArea", videoPath)
  hyperparameters["minAreaBody"] = getConfig(config, "minAreaBody", videoPath)
  hyperparameters["maxAreaBody"] = getConfig(config, "maxAreaBody", videoPath)
  hyperparameters["headSize"] = getConfig(config, "headSize", videoPath)
  hyperparameters["debugExtractParams"] = getConfig(config, "debugExtractParams", videoPath)
  hyperparameters["debugTracking"]      = getConfig(config, "debugTracking", videoPath)
  hyperparameters["debugExtractBack"]   = getConfig(config, "debugExtractBack", videoPath)
  hyperparameters["debugFindWells"]     = getConfig(config, "debugFindWells", videoPath)
  hyperparameters["debugPauseBetweenTrackAndParamExtract"] = getConfig(config, "debugPauseBetweenTrackAndParamExtract", videoPath)
  hyperparameters["headEmbeded"]        = getConfig(config, "headEmbeded", videoPath)
  
  hyperparameters["halfDiameterRoiBoutDetect"] = getConfig(config, "halfDiameterRoiBoutDetect", videoPath)
  hyperparameters["thresForDetectMovementWithRawVideo"] = getConfig(config, "thresForDetectMovementWithRawVideo", videoPath)
  hyperparameters["minNbPixelForDetectMovementWithRawVideo"] = getConfig(config, "minNbPixelForDetectMovementWithRawVideo", videoPath)
  hyperparameters["frameGapComparision"]        = getConfig(config, "frameGapComparision", videoPath)
  hyperparameters["wellOutputVideoDiameter"]    = getConfig(config, "wellOutputVideoDiameter", videoPath)
  hyperparameters["fillGapFrameNb"]             = getConfig(config, "fillGapFrameNb", videoPath)
  hyperparameters["minPixelDiffForBackExtract"] = getConfig(config, "minPixelDiffForBackExtract", videoPath)
  hyperparameters["outputFolder"]               = getConfig(config, "outputFolder", videoPath)
  hyperparameters["videoName"]                  = videoName[0:(len(videoName)-4)] # Need to improve this!
  hyperparameters["detectBoutMinNbFrames"]      = getConfig(config, "detectBoutMinNbFrames", videoPath)
  hyperparameters["detectBoutMinDist"]          = getConfig(config, "detectBoutMinDist", videoPath)
  hyperparameters["nbRowsOfWells"]              = getConfig(config, "nbRowsOfWells", videoPath)
  hyperparameters["nbWellsPerRows"]             = getConfig(config, "nbWellsPerRows", videoPath)
  hyperparameters["takeTheHeadClosestToTheCenter"] = getConfig(config, "takeTheHeadClosestToTheCenter", videoPath)
  
  hyperparameters["wellsAreRectangles"]          = getConfig(config, "wellsAreRectangles", videoPath)
  hyperparameters["plotOnlyOneTailPointForVisu"] = getConfig(config, "plotOnlyOneTailPointForVisu", videoPath)
  hyperparameters["trackingPointSizeDisplay"]    = getConfig(config, "trackingPointSizeDisplay", videoPath)
  
  hyperparameters["tailAngleSmoothingFactor"]        = getConfig(config, "tailAngleSmoothingFactor", videoPath)
  hyperparameters["tailAngleMedianFilter"]           = getConfig(config, "tailAngleMedianFilter", videoPath)
  hyperparameters["minDiffBetweenSubsequentBendAmp"] = getConfig(config, "minDiffBetweenSubsequentBendAmp", videoPath)
  
  hyperparameters["centerOfMassTailTracking"]    = getConfig(config, "centerOfMassTailTracking", videoPath)
  hyperparameters["freqAlgoPosFollow"]           = getConfig(config, "freqAlgoPosFollow", videoPath)
  
  hyperparameters["centerOfMassParamStep"]         = getConfig(config, "centerOfMassParamStep", videoPath)
  hyperparameters["centerOfMassParamSegStep"]      = getConfig(config, "centerOfMassParamSegStep", videoPath)
  hyperparameters["centerOfMassParamHalfDiam"]     = getConfig(config, "centerOfMassParamHalfDiam", videoPath)
  hyperparameters["headEmbededParamGaussianBlur"] = getConfig(config, "headEmbededParamGaussianBlur", videoPath)
  
  hyperparameters["headEmbededParamInitialAngle"] = getConfig(config, "headEmbededParamInitialAngle", videoPath)
  hyperparameters["detectBoutMinAngleDiff"]        = getConfig(config, "detectBoutMinAngleDiff", videoPath)
  
  hyperparameters["coverHorizontalPortionBelowForHeadDetect"] = getConfig(config, "coverHorizontalPortionBelowForHeadDetect", videoPath)
  hyperparameters["coverHorizontalPortionAboveForHeadDetect"] = getConfig(config, "coverHorizontalPortionAboveForHeadDetect", videoPath)
  hyperparameters["coverVerticalPortionRightForHeadDetect"] = getConfig(config, "coverVerticalPortionRightForHeadDetect", videoPath)
  
  hyperparameters["windowForLocalBendMinMaxFind"] = getConfig(config, "windowForLocalBendMinMaxFind", videoPath)
  
  hyperparameters["debugValidationVideoHeading"]  = getConfig(config, "debugValidationVideoHeading", videoPath)
  hyperparameters["headingCalculationMethod"]   = getConfig(config, "headingCalculationMethod", videoPath)
  
  hyperparameters["minFirstBendValue"]   = getConfig(config, "minFirstBendValue", videoPath)
  
  hyperparameters["videoWidth"]   = getConfig(config, "videoWidth",  videoPath)
  hyperparameters["videoHeight"]  = getConfig(config, "videoHeight", videoPath)
  
  hyperparameters["debugDetectMovWithRawVideo"] = getConfig(config, "debugDetectMovWithRawVideo", videoPath)
  hyperparameters["debugDetectMovWithRawVideoShowVid"] = getConfig(config, "debugDetectMovWithRawVideoShowVid", videoPath)
  
  hyperparameters["createValidationVideo"] = getConfig(config, "createValidationVideo", videoPath)
  
  hyperparameters["minProminenceForBendsDetect"] = getConfig(config, "minProminenceForBendsDetect", videoPath)
  
  hyperparameters["debugCoverHorizontalPortionBelow"] = getConfig(config, "debugCoverHorizontalPortionBelow", videoPath)
  
  hyperparameters["minNbPeaksForBoutDetect"] = getConfig(config, "minNbPeaksForBoutDetect", videoPath)
  
  hyperparameters["freeSwimmingTailTrackingMethod"] = getConfig(config, "freeSwimmingTailTrackingMethod", videoPath)
  
  hyperparameters["findContourPrecision"] = getConfig(config, "findContourPrecision", videoPath)
  
  hyperparameters["reloadWellPositions"] = getConfig(config, "reloadWellPositions", videoPath)
  hyperparameters["reloadBackground"]    = getConfig(config, "reloadBackground", videoPath)
  hyperparameters["thresholdForBlobImg"] = getConfig(config, "thresholdForBlobImg", videoPath)
  
  hyperparameters["minTailSize"] = getConfig(config, "minTailSize", videoPath)
  hyperparameters["maxTailSize"] = getConfig(config, "maxTailSize", videoPath)
  
  hyperparameters["debugTrackingPtExtreme"] = getConfig(config, "debugTrackingPtExtreme", videoPath)
  hyperparameters["debugTrackingPtExtremeLargeVerticals"] = getConfig(config, "debugTrackingPtExtremeLargeVerticals", videoPath)
  hyperparameters["debugTrackingThreshImg"] = getConfig(config, "debugTrackingThreshImg", videoPath)

  hyperparameters["erodeSize"]  = getConfig(config, "erodeSize", videoPath)
  hyperparameters["erodeIter"]  = getConfig(config, "erodeIter", videoPath)
  hyperparameters["dilateIter"] = getConfig(config, "dilateIter", videoPath)
  
  hyperparameters["headEmbededRemoveBack"] = getConfig(config, "headEmbededRemoveBack", videoPath)
  hyperparameters["extractBackWhiteBackground"] = getConfig(config, "extractBackWhiteBackground", videoPath)
  
  hyperparameters["addBlackCircleOfHalfDiamOnHeadForBoutDetect"] = getConfig(config, "addBlackCircleOfHalfDiamOnHeadForBoutDetect", videoPath)
  
  hyperparameters["doubleCheckBendMinMaxStatus"] = getConfig(config, "doubleCheckBendMinMaxStatus", videoPath)
  hyperparameters["removeFirstSmallBend"] = getConfig(config, "removeFirstSmallBend", videoPath)
  
  hyperparameters["coverPortionForHeadDetect"] = getConfig(config, "coverPortionForHeadDetect", videoPath)
  
  hyperparameters["tailExtremityMaxJugeDecreaseCoeff"] = getConfig(config, "tailExtremityMaxJugeDecreaseCoeff", videoPath)
  
  hyperparameters["firstFrameForTracking"] = getConfig(config, "firstFrameForTracking", videoPath)
  
  hyperparameters["findHeadPositionByUserInput"] = getConfig(config, "findHeadPositionByUserInput", videoPath)
  
  hyperparameters["invertBlackWhiteOnImages"] = getConfig(config, "invertBlackWhiteOnImages", videoPath)
  
  hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"] = getConfig(config, "headEmbededTailTrackFindMaxDepthInitialMaxDepth", videoPath)
  
  hyperparameters["debugHeadEmbededFindNextPoints"] = getConfig(config, "debugHeadEmbededFindNextPoints", videoPath)
  
  hyperparameters["headEmbededTeresaNicolson"] = getConfig(config, "headEmbededTeresaNicolson", videoPath)
  
  hyperparameters["boutEdgesWhereZeros"] = getConfig(config, "boutEdgesWhereZeros", videoPath)
  
  hyperparameters["noBoutsDetection"]    = getConfig(config, "noBoutsDetection", videoPath)
  
  hyperparameters["coordinatesOnlyBoutDetection"] = getConfig(config, "coordinatesOnlyBoutDetection", videoPath)

  hyperparameters["coordinatesOnlyBoutDetectionMinDist"] = getConfig(config, "coordinatesOnlyBoutDetectionMinDist", videoPath)

  hyperparameters["setPixDiffBoutDetectParameters"] = getConfig(config, "setPixDiffBoutDetectParameters", videoPath)
  
  hyperparameters["midlineIsInBlobTrackingOptimization"] = getConfig(config, "midlineIsInBlobTrackingOptimization", videoPath)
  
  hyperparameters["debugHeadingCalculation"] = getConfig(config, "debugHeadingCalculation", videoPath)
  
  hyperparameters["accentuateFrameForManualTailExtremityFind"] = getConfig(config, "accentuateFrameForManualTailExtremityFind", videoPath)
  
  hyperparameters["popUpAlgoFollow"] = getConfig(config, "popUpAlgoFollow", videoPath)
  
  hyperparameters["paramGaussianBlur"] = getConfig(config, "paramGaussianBlur", videoPath)
  
  hyperparameters["generateAllTimeTailAngleGraph"] = getConfig(config, "generateAllTimeTailAngleGraph", videoPath)
  
  hyperparameters["generateAllTimeTailAngleGraphLineWidth"] = getConfig(config, "generateAllTimeTailAngleGraphLineWidth", videoPath)
  
  hyperparameters["extractAdvanceZebraParameters"] = getConfig(config, "extractAdvanceZebraParameters", videoPath)
  
  hyperparameters["noWellDetection"] = getConfig(config, "noWellDetection", videoPath)
  
  hyperparameters["nbAnimalsPerWell"] = getConfig(config, "nbAnimalsPerWell", videoPath)
  
  hyperparameters["oneWellManuallyChosenTopLeft"] = getConfig(config, "oneWellManuallyChosenTopLeft", videoPath)
  hyperparameters["oneWellManuallyChosenBottomRight"] = getConfig(config, "oneWellManuallyChosenBottomRight", videoPath)
  
  hyperparameters["noChecksForBoutSelectionInExtractParams"] = getConfig(config, "noChecksForBoutSelectionInExtractParams", videoPath)
  
  hyperparameters["validationVideoPlotHeading"] = getConfig(config, "validationVideoPlotHeading", videoPath)
  
  hyperparameters["multipleHeadTrackingIterativelyRelaxAreaCriteria"] = getConfig(config, "multipleHeadTrackingIterativelyRelaxAreaCriteria", videoPath)
  
  hyperparameters["closePopUpWindowAtTheEnd"] = getConfig(config, "closePopUpWindowAtTheEnd", videoPath)
  
  hyperparameters["multipleAnimalTrackingAdvanceAlgorithm"] = getConfig(config, "multipleAnimalTrackingAdvanceAlgorithm", videoPath)
  
  hyperparameters["multipleAnimalTrackingAdvanceAlgorithmMarginX"] = getConfig(config, "multipleAnimalTrackingAdvanceAlgorithmMarginX", videoPath)
  hyperparameters["multipleAnimalTrackingAdvanceAlgorithmDist1"] = getConfig(config, "multipleAnimalTrackingAdvanceAlgorithmDist1", videoPath)
  hyperparameters["multipleAnimalTrackingAdvanceAlgorithmDist2"] = getConfig(config, "multipleAnimalTrackingAdvanceAlgorithmDist2", videoPath)
  
  hyperparameters["perBoutOutput"] = getConfig(config, "perBoutOutput", videoPath)
  hyperparameters["perBoutOutputVideoStartStopFrameMargin"] = getConfig(config, "perBoutOutputVideoStartStopFrameMargin", videoPath)
  hyperparameters["perBoutOutputYaxis"] = getConfig(config, "perBoutOutputYaxis", videoPath)
  
  hyperparameters["smoothTailHeadEmbeded"] = getConfig(config, "smoothTailHeadEmbeded", videoPath)
  hyperparameters["nbTailPoints"] = getConfig(config, "nbTailPoints", videoPath)
  
  hyperparameters["curvatureMedianFilterSmoothingWindow"] = getConfig(config, "curvatureMedianFilterSmoothingWindow", videoPath)
  
  hyperparameters["headEmbededParamTailDescentPixThreshStop"] = getConfig(config, "headEmbededParamTailDescentPixThreshStop", videoPath)
  
  hyperparameters["automaticallySetSomeOfTheHeadEmbededHyperparameters"] = getConfig(config, "automaticallySetSomeOfTheHeadEmbededHyperparameters", videoPath)
  hyperparameters["headEmbededAutoSet_ExtendedDescentSearchOption"] = getConfig(config, "headEmbededAutoSet_ExtendedDescentSearchOption", videoPath)
  hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] = getConfig(config, "headEmbededAutoSet_BackgroundExtractionOption", videoPath)
  
  hyperparameters["trackTail"] = getConfig(config, "trackTail", videoPath)
  
  hyperparameters["adjustDetectMovWithRawVideo"] = getConfig(config, "adjustDetectMovWithRawVideo", videoPath)
  
  hyperparameters["adjustHeadEmbededTracking"] = getConfig(config, "adjustHeadEmbededTracking", videoPath)
  hyperparameters["adjustHeadEmbeddedEyeTracking"] = getConfig(config, "adjustHeadEmbeddedEyeTracking", videoPath)
  hyperparameters["adjustFreelySwimTracking"] = getConfig(config, "adjustFreelySwimTracking", videoPath)
  hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] = getConfig(config, "adjustFreelySwimTrackingAutomaticParameters", videoPath)
  
  hyperparameters["overwriteFirstStepValue"] = getConfig(config, "overwriteFirstStepValue", videoPath)
  hyperparameters["overwriteLastStepValue"]  = getConfig(config, "overwriteLastStepValue", videoPath)
  hyperparameters["overwriteNbOfStepValues"] = getConfig(config, "overwriteNbOfStepValues", videoPath)
  
  hyperparameters["headEmbededParamTailDescentPixThreshStopOverwrite"] = getConfig(config, "headEmbededParamTailDescentPixThreshStopOverwrite", videoPath)
  
  hyperparameters["exitAfterBackgroundExtraction"] = getConfig(config, "exitAfterBackgroundExtraction", videoPath)
  
  hyperparameters["nbImagesForBackgroundCalculation"] = getConfig(config, "nbImagesForBackgroundCalculation", videoPath)
  
  hyperparameters["authorizedRelativeLengthTailEnd"] = getConfig(config, "authorizedRelativeLengthTailEnd", videoPath)
  
  hyperparameters["initialTailPortionMaxSegmentDiffAngleCutOffPos"] = getConfig(config, "initialTailPortionMaxSegmentDiffAngleCutOffPos", videoPath)
  hyperparameters["initialTailPortionMaxSegmentDiffAngleValue"] = getConfig(config, "initialTailPortionMaxSegmentDiffAngleValue", videoPath)
  
  hyperparameters["windowForBoutDetectWithAngle"] = getConfig(config, "windowForBoutDetectWithAngle", videoPath)
  
  hyperparameters["forceBlobMethodForHeadTracking"] = getConfig(config, "forceBlobMethodForHeadTracking", videoPath)
  
  hyperparameters["headEmbededRetrackIfWeirdInitialTracking"] = getConfig(config, "headEmbededRetrackIfWeirdInitialTracking", videoPath)
  
  hyperparameters["overwriteHeadEmbededParamGaussianBlur"] = getConfig(config, "overwriteHeadEmbededParamGaussianBlur", videoPath)
  
  hyperparameters["calculateAllTailAngles"] = getConfig(config, "calculateAllTailAngles", videoPath)
  
  hyperparameters["nbPointsToIgnoreAtCurvatureBeginning"] = getConfig(config, "nbPointsToIgnoreAtCurvatureBeginning", videoPath)
  
  hyperparameters["nbPointsToIgnoreAtCurvatureEnd"] = getConfig(config, "nbPointsToIgnoreAtCurvatureEnd", videoPath)
  
  hyperparameters["imagePreProcessMethod"] = getConfig(config, "imagePreProcessMethod", videoPath)
  hyperparameters["imagePreProcessParameters"] = getConfig(config, "imagePreProcessParameters", videoPath)
  
  hyperparameters["backgroundPreProcessMethod"] = getConfig(config, "backgroundPreProcessMethod", videoPath)
  hyperparameters["backgroundPreProcessParameters"] = getConfig(config, "backgroundPreProcessParameters", videoPath)
  
  hyperparameters["backgroundExtractionWithOnlyTwoFrames"] = getConfig(config, "backgroundExtractionWithOnlyTwoFrames", videoPath)
  
  hyperparameters["checkThatMovementOccurInVideo"] = getConfig(config, "checkThatMovementOccurInVideo", videoPath)
  hyperparameters["checkThatMovementOccurInVideoMedianFilterWindow"] = getConfig(config, "checkThatMovementOccurInVideoMedianFilterWindow", videoPath)
  
  hyperparameters["findRectangleWellArea"] = getConfig(config, "findRectangleWellArea", videoPath)
  hyperparameters["rectangleWellAreaImageThreshold"] = getConfig(config, "rectangleWellAreaImageThreshold", videoPath)
  hyperparameters["rectangleWellErodeDilateKernelSize"] = getConfig(config, "rectangleWellErodeDilateKernelSize", videoPath)
  hyperparameters["rectangularWellsInvertBlackWhite"] = getConfig(config, "rectangularWellsInvertBlackWhite", videoPath)
  hyperparameters["rectangularWellStretchPercentage"] = getConfig(config, "rectangularWellStretchPercentage", videoPath)
  hyperparameters["rectangleWellAreaTolerancePercentage"] = getConfig(config, "rectangleWellAreaTolerancePercentage", videoPath)

  hyperparameters["adjustRectangularWellsDetect"] = getConfig(config, "adjustRectangularWellsDetect", videoPath)
  
  hyperparameters["outputValidationVideoFps"] = getConfig(config, "outputValidationVideoFps", videoPath)
  
  hyperparameters["checkAllContourForTailExtremityDetect"] = getConfig(config, "checkAllContourForTailExtremityDetect", videoPath)
  hyperparameters["considerHighPointForTailExtremityDetect"] = getConfig(config, "considerHighPointForTailExtremityDetect", videoPath)
  
  hyperparameters["debugEyeTracking"]                   = getConfig(config, "debugEyeTracking", videoPath)
  hyperparameters["debugEyeTrackingAdvanced"]           = getConfig(config, "debugEyeTrackingAdvanced", videoPath)
  hyperparameters["eyeTracking"]                        = getConfig(config, "eyeTracking", videoPath)
  hyperparameters["headCenterToMidEyesPointDistance"]   = getConfig(config, "headCenterToMidEyesPointDistance", videoPath)
  hyperparameters["eyeBinaryThreshold"]                 = getConfig(config, "eyeBinaryThreshold", videoPath)
  hyperparameters["midEyesPointToEyeCenterMaxDistance"] = getConfig(config, "midEyesPointToEyeCenterMaxDistance", videoPath)
  hyperparameters["eyeHeadingSearchAreaHalfDiameter"]   = getConfig(config, "eyeHeadingSearchAreaHalfDiameter", videoPath)
  hyperparameters["headingLineValidationPlotLength"]    = getConfig(config, "headingLineValidationPlotLength", videoPath)
  hyperparameters["saveSuperStructToMatlab"]            = getConfig(config, "saveSuperStructToMatlab", videoPath)
  hyperparameters["validationVideoPlotAnimalNumber"]    = getConfig(config, "validationVideoPlotAnimalNumber", videoPath)
  hyperparameters["postProcessMultipleTrajectories"]    = getConfig(config, "postProcessMultipleTrajectories", videoPath)
  hyperparameters["postProcessMaxDistanceAuthorized"]   = getConfig(config, "postProcessMaxDistanceAuthorized", videoPath)
  hyperparameters["postProcessMaxDisapearanceFrames"]   = getConfig(config, "postProcessMaxDisapearanceFrames", videoPath)
  hyperparameters["computeEyesHeadingPlot"]             = getConfig(config, "computeEyesHeadingPlot", videoPath)
  hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = getConfig(config, "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax", videoPath)
  
  hyperparameters["fixedHeadPositionX"] = getConfig(config, "fixedHeadPositionX", videoPath)
  hyperparameters["fixedHeadPositionY"] = getConfig(config, "fixedHeadPositionY", videoPath)
  
  hyperparameters["recalculateForegroundImageBasedOnBodyArea"] = getConfig(config, "recalculateForegroundImageBasedOnBodyArea", videoPath)
  
  hyperparameters["detectMouthInsteadOfHeadTwoSides"] = getConfig(config, "detectMouthInsteadOfHeadTwoSides", videoPath)
  hyperparameters["findCenterOfAnimalByIterativelyDilating"] = getConfig(config, "findCenterOfAnimalByIterativelyDilating", videoPath)
  
  hyperparameters["backgroundExtractionForceUseAllVideoFrames"] = getConfig(config, "backgroundExtractionForceUseAllVideoFrames", videoPath)
  
  hyperparameters["readjustCenterOfMassIfNotInsideContour"] = getConfig(config, "readjustCenterOfMassIfNotInsideContour", videoPath)
  
  hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"] = getConfig(config, "onlyDoTheTrackingForThisNumberOfFrames", videoPath)
  
  hyperparameters["multipleROIsDefinedDuringExecution"] = getConfig(config, "multipleROIsDefinedDuringExecution", videoPath)
  
  hyperparameters["saveWellPositionsToBeReloadedNoMatterWhat"] = getConfig(config, "saveWellPositionsToBeReloadedNoMatterWhat", videoPath)
  hyperparameters["exitAfterWellsDetection"] = getConfig(config, "exitAfterWellsDetection", videoPath)
  
  hyperparameters["additionalOutputFolder"] = getConfig(config, "additionalOutputFolder", videoPath)
  hyperparameters["additionalOutputFolderOverwriteIfAlreadyExist"] = getConfig(config, "additionalOutputFolderOverwriteIfAlreadyExist", videoPath)
  
  hyperparameters["outputValidationVideoContrastImprovement"] = getConfig(config, "outputValidationVideoContrastImprovement", videoPath)
  hyperparameters["outputValidationVideoContrastImprovementQuartile"] = getConfig(config, "outputValidationVideoContrastImprovementQuartile", videoPath)
  
  hyperparameters["videoFPS"] = getConfig(config, "videoFPS", videoPath)
  hyperparameters["videoPixelSize"] = getConfig(config, "videoPixelSize", videoPath)
  
  hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"] = getConfig(config, "groupOfMultipleSameSizeAndShapeEquallySpacedWells", videoPath)
  
  hyperparameters["fasterMultiprocessing"] = getConfig(config, "fasterMultiprocessing", videoPath)
  
  hyperparameters["copyOriginalVideoToOutputFolderForValidation"] = getConfig(config, "copyOriginalVideoToOutputFolderForValidation", videoPath)
  
  hyperparameters["postProcessRemoveLowProbabilityDetection"] = getConfig(config, "postProcessRemoveLowProbabilityDetection", videoPath)
  hyperparameters["postProcessLowProbabilityDetectionThreshold"] = getConfig(config, "postProcessLowProbabilityDetectionThreshold", videoPath)
  hyperparameters["postProcessRemovePointsOnBordersMargin"] = getConfig(config, "postProcessRemovePointsOnBordersMargin", videoPath)
  hyperparameters["postProcessRemovePointsAwayFromMainTrajectory"] = getConfig(config, "postProcessRemovePointsAwayFromMainTrajectory", videoPath)
  hyperparameters["postProcessRemovePointsAwayFromMainTrajectoryThreshold"] = getConfig(config, "postProcessRemovePointsAwayFromMainTrajectoryThreshold", videoPath)
  
  hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"] = getConfig(config, "reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise", videoPath)
  
  hyperparameters["tailAnglesHeatMap"] = getConfig(config, "tailAnglesHeatMap", videoPath)
  hyperparameters["tailAnglesHeatMapNbPointsToTakeIntoAccount"] = getConfig(config, "tailAnglesHeatMapNbPointsToTakeIntoAccount", videoPath)
  
  hyperparameters["setBackgroundToImageMedian"] = getConfig(config, "setBackgroundToImageMedian", videoPath)
  
  hyperparameters["backgroundSubtractorKNN"] = getConfig(config, "backgroundSubtractorKNN", videoPath)
  
  hyperparameters["postProcessLowProbabilityDetectionPercentOfMaximum"] = getConfig(config, "postProcessLowProbabilityDetectionPercentOfMaximum", videoPath)
  
  hyperparameters["createPandasDataFrameOfParameters"] = getConfig(config, "createPandasDataFrameOfParameters", videoPath)
  
  hyperparameters["frameStepForDistanceCalculation"] = getConfig(config, "frameStepForDistanceCalculation", videoPath)
  
  hyperparameters["addBlackLineToImg_Width"] = getConfig(config, "addBlackLineToImg_Width", videoPath)
  
  hyperparameters["headEmbededMaxAngleBetweenSubsequentSegments"] = getConfig(config, "headEmbededMaxAngleBetweenSubsequentSegments", videoPath)
  
  hyperparameters["saveBodyMask"] = getConfig(config, "saveBodyMask", videoPath)
  hyperparameters["bodyMask_addWhitePoints"] = getConfig(config, "bodyMask_addWhitePoints", videoPath)
  hyperparameters["bodyMask_saveAsLabelMeJsonFormat"] = getConfig(config, "bodyMask_saveAsLabelMeJsonFormat", videoPath)
  hyperparameters["bodyMask_saveAsPngMask"] = getConfig(config, "bodyMask_saveAsPngMask", videoPath)
  hyperparameters["saveBodyMaskResampleContourNbPoints"] = getConfig(config, "saveBodyMaskResampleContourNbPoints", videoPath)
  hyperparameters["dontDeleteOutputFolderIfAlreadyExist"] = getConfig(config, "dontDeleteOutputFolderIfAlreadyExist", videoPath)
  hyperparameters["bodyMask_saveDataForAllFrames"] = getConfig(config, "bodyMask_saveDataForAllFrames", videoPath)
  
  hyperparameters["trackingDL"] = getConfig(config, "trackingDL", videoPath)
  hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"] = getConfig(config, "trackingDLdicotomySearchOfOptimalBlobArea", videoPath)
  hyperparameters["applySimpleThresholdOnPredictedMask"] = getConfig(config, "applySimpleThresholdOnPredictedMask", videoPath)
  hyperparameters["simpleThresholdCheckMinForMaxCountour"] = getConfig(config, "simpleThresholdCheckMinForMaxCountour", videoPath)
  
  hyperparameters["rectangularWellMinMaxXandYmethod"] = getConfig(config, "rectangularWellMinMaxXandYmethod", videoPath)
  hyperparameters["rectangularWellMinMaxXandYmethodMargin"] = getConfig(config, "rectangularWellMinMaxXandYmethodMargin", videoPath)
  
  hyperparameters["addOneFrameAtTheEndForBoutDetection"] = getConfig(config, "addOneFrameAtTheEndForBoutDetection", videoPath)
  
  hyperparameters["boutsMinNbFrames"] = getConfig(config, "boutsMinNbFrames", videoPath)
  
  hyperparameters["trackOnlyOnROI_halfDiameter"] = getConfig(config, "trackOnlyOnROI_halfDiameter", videoPath)
  
  hyperparameters["detectMovementWithRawVideoInsideTracking"] = getConfig(config, "detectMovementWithRawVideoInsideTracking", videoPath)
  
  hyperparameters["fishTailTrackingDifficultBackground"] = getConfig(config, "fishTailTrackingDifficultBackground", videoPath)
  
  hyperparameters["tryCreatingFolderUntilSuccess"] =  getConfig(config, "tryCreatingFolderUntilSuccess", videoPath)
  
  hyperparameters["searchPreviousFramesIfCurrentFrameIsCorrupted"] =  getConfig(config, "searchPreviousFramesIfCurrentFrameIsCorrupted", videoPath)
  
  hyperparameters["reduceImageResolutionPercentage"] = getConfig(config, "reduceImageResolutionPercentage", videoPath)
  
  hyperparameters["trackingMethod"] = getConfig(config, "trackingMethod", videoPath)
  
  hyperparameters["smoothTailHeadEmbededNbOfIterations"] = getConfig(config, "smoothTailHeadEmbededNbOfIterations", videoPath)
  
  hyperparameters["saveCurvaturePlots"] = getConfig(config, "saveCurvaturePlots", videoPath)
  hyperparameters["saveTailAngleGraph"] = getConfig(config, "saveTailAngleGraph", videoPath)
  hyperparameters["saveSubVideo"]       = getConfig(config, "saveSubVideo", videoPath)
  hyperparameters["saveCurvatureData"]  = getConfig(config, "saveCurvatureData", videoPath)
  
  hyperparameters["colorMapCurvature"]  = getConfig(config, "colorMapCurvature", videoPath)
  
  hyperparameters["eyeTrackingHeadEmbeddedWidth"]        = getConfig(config, "eyeTrackingHeadEmbeddedWidth", videoPath)
  hyperparameters["eyeTrackingHeadEmbeddedWidthLeft"]    = getConfig(config, "eyeTrackingHeadEmbeddedWidthLeft", videoPath)
  hyperparameters["eyeTrackingHeadEmbeddedWidthRight"]   = getConfig(config, "eyeTrackingHeadEmbeddedWidthRight", videoPath)
  hyperparameters["eyeTrackingHeadEmbeddedHalfDiameter"] = getConfig(config, "eyeTrackingHeadEmbeddedHalfDiameter", videoPath)
  
  hyperparameters["eyeTrackingHeadEmbeddedWithSegment"]  = getConfig(config, "eyeTrackingHeadEmbeddedWithSegment", videoPath)
  hyperparameters["eyeTrackingHeadEmbeddedWithEllipse"]  = getConfig(config, "eyeTrackingHeadEmbeddedWithEllipse", videoPath)
  hyperparameters["eyeFilterKernelSize"] = getConfig(config, "eyeFilterKernelSize", videoPath)
  
  hyperparameters["noPreProcessingOfImageForBoutDetection"] = getConfig(config, "noPreProcessingOfImageForBoutDetection", videoPath)
  
  hyperparameters["invertColorsForHeadEmbeddedEyeTracking"] = getConfig(config, "invertColorsForHeadEmbeddedEyeTracking", videoPath)
  hyperparameters["improveContrastForEyeDetectionOfHeadEmbedded"] = getConfig(config, "improveContrastForEyeDetectionOfHeadEmbedded", videoPath)
  
  if hyperparameters["tailAnglesHeatMap"]:
    hyperparameters["calculateAllTailAngles"] = 1
  
  
  if len(argv) > 5 and not(argv[0] == "getTailExtremityFirstFrame"):
    i = 5
    while i < len(argv):
      print("command line hyperparameter change:", argv[i], argv[i+1])
      
      if not(argv[i] in ["debugPauseBetweenTrackAndParamExtract", "outputFolder", "coverPortionForHeadDetect", "freeSwimmingTailTrackingMethod", "findContourPrecision", "headingCalculationMethod", "additionalOutputFolder"]):
        try:
          hyperparameters[argv[i]] = int(argv[i+1])
          config[argv[i]]          = int(argv[i+1])
        except:
          hyperparameters[argv[i]] = float(argv[i+1])
          config[argv[i]]          = float(argv[i+1])
        
      else:
        hyperparameters[argv[i]] = argv[i+1]
        config[argv[i]]          = argv[i+1]
      
      i = i + 2
  
  
  if hyperparameters["setPixDiffBoutDetectParameters"] > 0:
    hyperparameters["debugPauseBetweenTrackAndParamExtract"] = "justExtractParamFromPreviousTrackData"
    hyperparameters["createValidationVideo"]                 = 1 
    hyperparameters["reloadBackground"]                      = 1 
    hyperparameters["debugDetectMovWithRawVideo"]            = 1
    hyperparameters["debugDetectMovWithRawVideoShowVid"]     = 1
    hyperparameters["reloadWellPositions"]                   = 1
    
  if hyperparameters["setPixDiffBoutDetectParameters"] == 2:
    hyperparameters["debugDetectMovWithRawVideoShowVid"]     = 0
  
  # if globalVariables["limitedVersion"] == 1:
    # limitNbFrames = 1000
    # if hyperparameters["lastFrame"] - hyperparameters["firstFrame"] > limitNbFrames:
      # hyperparameters["lastFrame"] = int(hyperparameters["firstFrame"]) + limitNbFrames
  
  return [hyperparameters, config]
  
  
def getHyperparametersSimple(configTemp):
  hyperparameters = configDefault.copy()
  for index in configTemp:
    hyperparameters[index] = configTemp[index]
  return hyperparameters

