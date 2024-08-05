from pathlib import Path
import copy
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

CONFIG_DEFAULT = \
{
  "videoFPS" : 0,
  "videoPixelSize" : 0,
  "firstFrameForTracking" : -1,
  "adjustDetectMovWithRawVideo" : 0,
  "adjustHeadEmbededTracking" : 0,
  "adjustFreelySwimTracking" : 0,
  "adjustFreelySwimTrackingAutomaticParameters" : 0,
  "adjustRectangularWellsDetect" : 0,
  "debugExtractParams" : 0,
  "debugTracking" : 0,
  "debugTrackingPtExtreme" : 0,
  "debugTrackingPtExtremeLargeVerticals" : 0,
  "debugTrackingThreshImg" : 0,
  "debugExtractBack" : 0,
  "debugFindWells" : 0,
  "debugHeadingCalculation" : 0,
  "debugValidationVideoHeading" : 0,
  "debugDetectMovWithRawVideo" : 0,
  "debugDetectMovWithRawVideoShowVid" : 1,
  "debugCoverHorizontalPortionBelow" : 0,
  "debugHeadEmbededFindNextPoints" : 0,
  "debugEyeTracking" : 0,
  "debugEyeTrackingAdvanced" : 0,
  "onlyDoTheTrackingForThisNumberOfFrames": 0,
  "createValidationVideo" : 1,
  "copyOriginalVideoToOutputFolderForValidation" : 0,
  "calculateAllTailAngles" : 0,
  "freqAlgoPosFollow" : 0,
  "popUpAlgoFollow" : 0,
  "closePopUpWindowAtTheEnd" : 1,
  "reloadWellPositions" : 0,
  "reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise" : 0,
  "reloadBackground" : 0,
  "saveWellPositionsToBeReloadedNoMatterWhat" : 0,
  "backgroundExtractionForceUseAllVideoFrames" : 0,
  "updateBackgroundAtInterval" : 0,
  "useFirstFrameAsBackground" : 0,
  "exitAfterBackgroundExtraction" : 0,
  "exitAfterWellsDetection" : 0,
  "fasterMultiprocessing" : 0,
  "trackOnlyOnROI_halfDiameter" : 0,
  "tryCreatingFolderUntilSuccess" : 1,
  "searchPreviousFramesIfCurrentFrameIsCorrupted" : 1,
  "reduceImageResolutionPercentage" : 1,
  "trackingMethod" : "",
  "saveAllDataEvenIfNotInBouts" : 0,

  "setPixDiffBoutDetectParameters" : 0,

  "nbAnimalsPerWell" : 1,
  "trackTail" : 1,
  "multipleAnimalTrackingAdvanceAlgorithm" : 0,
  "multipleAnimalTrackingAdvanceAlgorithmMarginX" : 30,
  "multipleAnimalTrackingAdvanceAlgorithmDist1" : 50,
  "multipleAnimalTrackingAdvanceAlgorithmDist2" : 400,
  "findHeadPositionByUserInput" : 0,
  "accentuateFrameForManualTailExtremityFind" : 1,
  "outputFolder" : paths.getDefaultZZoutputFolder(),
  "onlyTrackThisOneWell" : -1,
  "noWellDetection" : 0,
  "multipleROIsDefinedDuringExecution" : 0,
  "oneWellManuallyChosenTopLeft" : [],
  "oneWellManuallyChosenBottomRight" : [],
  "headEmbeded" : 0,
  "headEmbededTeresaNicolson" : 0,
  "headEmbededRemoveBack" : 0,
  "extractBackWhiteBackground" : 1,
  "extractAdvanceZebraParameters" : 1,
  "takeTheHeadClosestToTheCenter" : 0,
  "backgroundSubtractorKNN" : 0,

  "groupOfMultipleSameSizeAndShapeEquallySpacedWells" : 0,
  "wellsAreRectangles" : 0,
  "rectangularWellMinMaxXandYmethod"       : 0,
  "rectangularWellMinMaxXandYmethodMargin" : 0,
  "findRectangleWellArea"                : 165000,
  "rectangleWellAreaImageThreshold"      : 105,
  "rectangleWellErodeDilateKernelSize"   : 20,
  "rectangularWellsInvertBlackWhite"     : 0,
  "rectangularWellStretchPercentage"     : 5,
  "rectangleWellAreaTolerancePercentage" : 20,

  "nbWells" : -1,
  "nbRowsOfWells"  : 0,
  "nbWellsPerRows" : 0,
  "coverHorizontalPortionBelowForHeadDetect" : -1,
  "coverHorizontalPortionAboveForHeadDetect" : -1,
  "coverVerticalPortionRightForHeadDetect"   : -1,
  "coverPortionForHeadDetect" : "Null",
  "centerOfMassTailTracking" : 0,
  "freeSwimmingTailTrackingMethod" : "tailExtremityDetect",
  "invertBlackWhiteOnImages" : 0,
  "generateAllTimeTailAngleGraph" : 0,
  "generateAllTimeTailAngleGraphLineWidth" : 0.3,

  "imagePreProcessMethod" : 0,
  "imagePreProcessParameters" : [],

  "backgroundPreProcessMethod" : 0,
  "backgroundPreProcessParameters" : [],

  "addBlackLineToImg_Width" : 0,

  "minWellDistanceForWellDetection" : 250,
  "wellOutputVideoDiameter" : -1,

  "nbImagesForBackgroundCalculation" : 60,
  "minPixelDiffForBackExtract" : 20,
  "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax" : 0,
  "backgroundExtractionWithOnlyTwoFrames" : 0,
  "checkThatMovementOccurInVideo" : 0,
  "checkThatMovementOccurInVideoMedianFilterWindow" : 11,
  "setBackgroundToImageMedian" : 0,
  "firstFrameForBackExtract" : -1,
  "lastFrameForBackExtract"  : -1,

  "findContourPrecision" : "CHAIN_APPROX_SIMPLE",

  "paramGaussianBlur" : 31,
  "erodeSize"  : 3,
  "erodeIter"  : 1,
  "dilateIter" : 2,
  "thresholdForBlobImg" : 200,
  "multipleHeadTrackingIterativelyRelaxAreaCriteria" : 0,
  "minArea" : -1,
  "maxArea" : -1,
  "minAreaBody" : -1,
  "maxAreaBody" : -1,
  "headSize" : -1,
  "minTailSize" : 3,
  "maxTailSize" : 60,
  "tailExtremityMaxJugeDecreaseCoeff" : 0.3,
  "checkAllContourForTailExtremityDetect" : 0,
  "considerHighPointForTailExtremityDetect" : 1,
  "midlineIsInBlobTrackingOptimization" : 1,
  "nbTailPoints" : 10,
  "forceBlobMethodForHeadTracking" : 0,
  "postProcessMultipleTrajectories" : 0,
  "postProcessMaxDistanceAuthorized" : 100000000000000000000000000000000000000000000,
  "postProcessMaxDisapearanceFrames" : 100,
  "postProcessRemoveLowProbabilityDetection" : 0,
  "postProcessLowProbabilityDetectionThreshold" : 1,
  "postProcessLowProbabilityDetectionPercentOfMaximum" : 0,
  "postProcessRemovePointsOnBordersMargin" : 0,
  "postProcessRemovePointsAwayFromMainTrajectory" : 0,
  "postProcessRemovePointsAwayFromMainTrajectoryThreshold" : 2.5,
  "fixedHeadPositionX" : -1,
  "fixedHeadPositionY" : -1,
  "recalculateForegroundImageBasedOnBodyArea" : 0,
  "detectMouthInsteadOfHeadTwoSides" : 0,
  "findCenterOfAnimalByIterativelyDilating" : 0,
  "readjustCenterOfMassIfNotInsideContour": 0,

  "eyeTracking" : 0,
  "adjustHeadEmbeddedEyeTracking": 0,
  "invertColorsForHeadEmbeddedEyeTracking": 0,
  "improveContrastForEyeDetectionOfHeadEmbedded": 1,
  "eyeTrackingHeadEmbeddedWithSegment" : 0,
  "eyeTrackingHeadEmbeddedWithEllipse" : 0,
  "eyeFilterKernelSize" : 7,
  "headCenterToMidEyesPointDistance" : 5,
  "eyeBinaryThreshold" : 50,
  "midEyesPointToEyeCenterMaxDistance" : 10,
  "eyeHeadingSearchAreaHalfDiameter" : 40,
  "headingLineValidationPlotLength" : 10,
  "eyeTrackingHeadEmbeddedWidth" : 4,
  "eyeTrackingHeadEmbeddedWidthLeft"  : 0,
  "eyeTrackingHeadEmbeddedWidthRight" : 0,
  "eyeTrackingHeadEmbeddedHalfDiameter" : 15,

  "backCalculationStep" : -1,
  "step" : -1,
  "overwriteFirstStepValue" : 0,
  "overwriteLastStepValue"  : 0,
  "overwriteNbOfStepValues" : 1,
  "nbList" : -1,
  "expDecreaseFactor" : -1,
  "headEmbededMaxAngleBetweenSubsequentSegments" : 0,

  "automaticallySetSomeOfTheHeadEmbededHyperparameters" : 0,
  "headEmbededAutoSet_ExtendedDescentSearchOption" : 0,
  "headEmbededAutoSet_BackgroundExtractionOption"  : 0,
  "headEmbededParamInitialAngle" : 0.78539816339,
  "headEmbededParamGaussianBlur" : 13,
  "authorizedRelativeLengthTailEnd" : 0.85,
  "overwriteHeadEmbededParamGaussianBlur" : 0,
  "headEmbededParamTailDescentPixThreshStop" : 150,
  "headEmbededParamTailDescentPixThreshStopOverwrite" : -1,
  "headEmbededTailTrackFindMaxDepthInitialMaxDepth" : 300,
  "centerOfMassParamStep" : 25,
  "centerOfMassParamSegStep" : 5,
  "centerOfMassParamHalfDiam" : 13,
  "initialTailPortionMaxSegmentDiffAngleCutOffPos" : 0.15,
  "initialTailPortionMaxSegmentDiffAngleValue" : 1,
  "headEmbededRetrackIfWeirdInitialTracking": 0,

  "headingCalculationMethod" : "calculatedWithHead",

  "thresAngleBoutDetect" : -1,
  "windowForBoutDetectWithAngle" : 10,
  "thresForDetectMovementWithRawVideo" : 0,
  "minNbPixelForDetectMovementWithRawVideo" : 0,
  "frameGapComparision" : 1,
  "halfDiameterRoiBoutDetect" : 100,
  "fillGapFrameNb" : 5,
  "detectMovementWithRawVideoInsideTracking" : 0,
  "addBlackCircleOfHalfDiamOnHeadForBoutDetect" : 0,
  "boutEdgesWhereZeros" : 0,
  "noBoutsDetection" : 0,
  "addOneFrameAtTheEndForBoutDetection" : 0,
  "noPreProcessingOfImageForBoutDetection": 0,
  "coordinatesOnlyBoutDetection": 0,
  "coordinatesOnlyBoutDetectionMinDist": 0,

  "boutsMinNbFrames" : 1,
  "noChecksForBoutSelectionInExtractParams" : 1,
  "detectBoutMinNbFrames" : 2,
  "detectBoutMinDist" : 4,
  "detectBoutMinAngleDiff" : -1,
  "minNbPeaksForBoutDetect" : 1,

  "tailAngleSmoothingFactor" : 0.001,
  "tailAngleMedianFilter" : 3,

  "minFirstBendValue" : -1,
  "minDiffBetweenSubsequentBendAmp" : 0.02,
  "windowForLocalBendMinMaxFind" : 1,
  "minProminenceForBendsDetect" : 0.01,
  "doubleCheckBendMinMaxStatus" : 1,
  "removeFirstSmallBend" : 0,

  "saveSuperStructToMatlab" : 0,
  "removeLargeInstantaneousDistanceData" : 0,

  "plotOnlyOneTailPointForVisu" : 0,
  "trackingPointSizeDisplay" : 1,
  "validationVideoPlotHeading" : 1,
  "validationVideoPlotAnimalNumber": 0,

  "perBoutOutput" : 0,
  "perBoutOutputVideoStartStopFrameMargin" : 0,
  "perBoutOutputYaxis" : 0,
  "smoothTailHeadEmbeded" : -1,
  "smoothTailHeadEmbededNbOfIterations" : 1,
  "alternativeCurvatureCalculation" : 0,
  "curvatureMedianFilterSmoothingWindow" : 3,
  "nbPointsToIgnoreAtCurvatureBeginning" : 0,
  "nbPointsToIgnoreAtCurvatureEnd" : 0,
  "colorMapCurvature"  : "BrBG",
  "saveCurvaturePlots" : 0,
  "saveTailAngleGraph" : 0,
  "saveSubVideo"       : 0,
  "saveCurvatureData"  : 0,
  "maxCurvatureValues"     : 0,
  "curvatureXaxisNbFrames" : 0,

  "tailAnglesHeatMap" : 0,
  "tailAnglesHeatMapNbPointsToTakeIntoAccount" : 8,

  "createPandasDataFrameOfParameters" : 0,
  "frameStepForDistanceCalculation" : 0,

  "additionalOutputFolder" : "",
  "additionalOutputFolderOverwriteIfAlreadyExist" : 0,
  "outputValidationVideoContrastImprovement" : 0,
  "outputValidationVideoContrastImprovementQuartile" : 0.01,
  "outputValidationVideoFps" : -1,

  "computeEyesHeadingPlot": 0,

  "saveBodyMask": 0,
  "bodyMask_addWhitePoints": 0,
  "bodyMask_saveAsLabelMeJsonFormat": 0,
  "bodyMask_saveAsPngMask": 0,
  "saveBodyMaskResampleContourNbPoints": 0,
  "dontDeleteOutputFolderIfAlreadyExist": 0,
  "bodyMask_saveDataForAllFrames": 0,

  "trackingDL": 0,
  "unet": 0,
  "trackingDLdicotomySearchOfOptimalBlobArea": 0,
  "applySimpleThresholdOnPredictedMask": 0,
  "simpleThresholdCheckMinForMaxCountour": 0,
  "applyQuantileInDLalgo": 0,

  "fishTailTrackingDifficultBackground": 0,

  "firstFrame": 1,
  "lastFrame": 0,
  "videoWidth": 0,
  "videoHeight": 0,

  "storeH5": 0,
}


def getHyperparameters(configFile, videoName, videoPath, argv):
  hyperparameters = copy.deepcopy(CONFIG_DEFAULT)
  hyperparameters["videoName"], _ = os.path.splitext(videoName)

  cap = zzVideoReading.VideoCapture(videoPath) if videoPath else None
  if cap is None or not cap.isOpened():
    print("Error opening video stream or file in getConfig")
  else:  # get defaults from video
    hyperparameters["lastFrame"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    hyperparameters["videoWidth"] = int(cap.get(3))
    hyperparameters["videoHeight"] = int(cap.get(4))

  if isinstance(configFile, str):
    with open(configFile) as f:
      config = json.load(f)
  else:
    assert isinstance(configFile, dict)
    config = configFile

  if "parentConfigFiles" in config:
    for parentConfigFile in config["parentConfigFiles"]:
      with open(os.path.join(cur_dir_path2, parentConfigFile)) as f2:
        parentConfig = json.load(f2)
        parentConfig.update(config)
        config = parentConfig

  hyperparameters.update(copy.deepcopy(config))

  if argv and argv[0] != "getTailExtremityFirstFrame":
    overridenParameters = {param: argv[i+1] for i, param in enumerate(argv) if str(param) in hyperparameters}
    for param, value in overridenParameters.items():
      print("command line hyperparameter change:", param, value)

      if param == 'createValidationVideo':
        if 'savePathToOriginalVideoForValidationVideo' in config:
          del config['savePathToOriginalVideoForValidationVideo']
          del hyperparameters['savePathToOriginalVideoForValidationVideo']

      if param not in {"outputFolder", "coverPortionForHeadDetect", "freeSwimmingTailTrackingMethod",
                       "findContourPrecision", "headingCalculationMethod", "additionalOutputFolder"}:
        try:
          overridenParameters[param] = int(value)
        except ValueError:
          overridenParameters[param] = float(value)

    hyperparameters.update(overridenParameters)
    config.update(overridenParameters)

  if hyperparameters['coordinatesOnlyBoutDetection']:
    hyperparameters['detectMovementWithRawVideoInsideTracking'] = 0

  if hyperparameters["tailAnglesHeatMap"]:
    hyperparameters["calculateAllTailAngles"] = 1

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

  return hyperparameters, config


def getHyperparametersSimple(configTemp):
  hyperparameters = copy.deepcopy(CONFIG_DEFAULT)
  for key in ('firstFrame', 'lastFrame', 'videoWidth', 'videoHeight'):
    del hyperparameters[key]
  hyperparameters.update(copy.deepcopy(configTemp))
  return hyperparameters
