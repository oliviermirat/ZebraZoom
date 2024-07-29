import os
import sys

import zebrazoom.code.paths as paths


def launchZebraZoom(args):
  from zebrazoom.GUIAllPy import ZebraZoomApp
  print("The data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
  app = ZebraZoomApp(sys.argv)
  sys.exit(app.exec())
  
def selectZZoutput(args):
  from zebrazoom.GUIAllPy import ZebraZoomApp
  app = ZebraZoomApp(sys.argv)
  print("The data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
  app.askForZZoutputLocation()
  sys.exit(app.exec())

def getTailExtremityFirstFrame(args):
  from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
  __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
  getTailExtremityFirstFrame(args.pathToVideo, args.videoName, args.videoExt, args.configFile, args.hyperparameters)

def recreateSuperStruct(args):
  from zebrazoom.recreateSuperStruct import recreateSuperStruct
  __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
  recreateSuperStruct(args.pathToVideo, args.videoName, args.videoExt, args.configFile, args.hyperparameters)

def convertSeqToAvi(args):
  from zebrazoom.videoFormatConversion.seq_to_avi import sqb_convert_to_avi
  sqb_convert_to_avi(args.path, args.videoName, args.codec, args.lastFrame)

def convertSeqToAviThenLaunchTracking(args):
  from zebrazoom.videoFormatConversion.seq_to_avi import sqb_convert_to_avi
  from zebrazoom.zebraZoomVideoAnalysis import ZebraZoomVideoAnalysis
  from pathlib import Path
  import time
  path2      = Path(args.path).parent
  print("Launching the convertion from seq to avi")
  sqb_convert_to_avi(args.path, args.videoName, args.codec, args.lastFrame)
  print("small break start")
  time.sleep(2)
  print("Launching the tracking, the data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
  __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
  ZebraZoomVideoAnalysis(path2, args.videoName, 'avi', args.configFile, args.hyperparameters, useGUI=False).run()

def DL_createMask(args):
  from zebrazoom.code.deepLearningFunctions.labellingFunctions import createMask
  pathToImgFolder = args.pathToImgFolder
  if not(os.path.exists(pathToImgFolder)):
    pathToImgFolder = os.path.join(paths.getDefaultZZoutputFolder(), args.pathToImgFolder, 'PNGImages')
  createMask(pathToImgFolder)

def sleepVsMoving(args):
  from zebrazoom.code.dataPostProcessing.findSleepVsMoving import calculateSleepVsMovingPeriods
  calculateSleepVsMovingPeriods(paths.getDefaultZZoutputFolder(), args.videoName, args.speedThresholdForMoving, args.notMovingNumberOfFramesThresholdForSleep,
                                args.maxDistBetweenTwoPointsInsideSleepingPeriod, args.specifiedStartTime, args.distanceTravelledRollingMedianFilter,
                                args.videoPixelSize, args.videoFPS)

def firstSleepingTimeAfterSpecifiedTime(args):
  from zebrazoom.code.dataPostProcessing.findSleepVsMoving import firstSleepingTimeAfterSpecifiedTime
  pathToZZoutput = paths.getDefaultZZoutputFolder()
  firstSleepingTimeAfterSpecifiedTime(args.pathToZZoutput, args.videoName, args.specifiedTime, args.wellNumber)

def numberOfSleepingAndMovingTimesInTimeRange(args):
  from zebrazoom.code.dataPostProcessing.findSleepVsMoving import numberOfSleepingAndMovingTimesInTimeRange
  numberOfSleepingAndMovingTimesInTimeRange(paths.getDefaultZZoutputFolder(), args.videoName, args.specifiedStartTime, args.specifiedEndTime, args.wellNumber)

def numberOfSleepBoutsInTimeRange(args):
  from zebrazoom.code.dataPostProcessing.findSleepVsMoving import numberOfSleepBoutsInTimeRange
  numberOfSleepBoutsInTimeRange(paths.getDefaultZZoutputFolder(), args.videoName, args.minSleepLenghtDurationThreshold, args.wellNumber,
                                args.specifiedStartTime, args.specifiedEndTime)

def calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshod(args):
  from zebrazoom.dataAnalysis.postProcessingFromCommandLine.postProcessingFromCommandLine import calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold
  calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold(paths.getRootDataFolder(), args.experimentName, args.thresholdInDegrees)

def kinematicParametersAnalysis(args):
  from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis
  kinematicParametersAnalysis(sys)

def kinematicParametersAnalysisWithMedianPerGenotype(args):
  from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis
  kinematicParametersAnalysis(sys, 1)

def clusteringAnalysis(args):
  from zebrazoom.clusteringAnalysis import clusteringAnalysis
  clusteringAnalysis(sys)

def clusteringAnalysisPerFrame(args):
  from zebrazoom.clusteringAnalysisPerFrame import clusteringAnalysisPerFrame
  clusteringAnalysisPerFrame(sys)

def kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection(args):
  from zebrazoom.kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection import kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection
  kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection(sys)

def visualizeMovingAndSleepingTime(args):
  from zebrazoom.code.GUI.readValidationVideo import readValidationVideo
  import pandas as pd
  df = pd.read_excel(os.path.join(paths.getDefaultZZoutputFolder(), args.videoName, "sleepVsMoving_" + args.videoName + ".xlsx"))
  nbWells = int(len(df.columns)/3)

  if args.movingOrSleeping == "movingTime":
    framesToShow = df[["moving_" + str(i) for i in range(0, nbWells)]].to_numpy()
  else:
    assert args.movingOrSleeping == "sleepingTime"
    framesToShow = df[["sleep_" + str(i) for i in range(0, nbWells)]].to_numpy()
  readValidationVideo("", args.videoName, -1, -1, 0, 1, framesToShow)

def createDistanceBetweenFramesExcelFile(args):
  from zebrazoom.dataAnalysis.createCustomDataStructure.createDistanceBetweenFramesExcelFile import createDistanceBetweenFramesExcelFile
  from zebrazoom.GUIAllPy import PlainApplication
  app = PlainApplication(sys.argv)
  createDistanceBetweenFramesExcelFile(paths.getDefaultZZoutputFolder(), args.videoFPS, args.videoPixelSize) # fps, pixelSize

def createDistanceSpeedHeadingDeltaHeadingExcelFile(args):
  from zebrazoom.dataAnalysis.createCustomDataStructure.createDistanceSpeedHeadingDeltaHeadingExcelFile import createDistanceSpeedHeadingDeltaHeadingExcelFile
  from zebrazoom.GUIAllPy import PlainApplication
  app = PlainApplication(sys.argv)
  createDistanceSpeedHeadingDeltaHeadingExcelFile(paths.getDefaultZZoutputFolder(), args.videoFPS, args.videoPixelSize) # fps, pixelSize

def removeLargeInstantaneousDistanceData(args):
  from zebrazoom.dataAnalysis.createCustomDataStructure.removeLargeInstantaneousDistanceData import removeLargeInstantaneousDistanceData
  from zebrazoom.GUIAllPy import PlainApplication
  app = PlainApplication(sys.argv)
  removeLargeInstantaneousDistanceData(paths.getDefaultZZoutputFolder(), args.maxDistance)

def filterLatencyAndMergeBoutsInSameTrials(args):
  from zebrazoom.dataAnalysis.createCustomDataStructure.filterLatencyAndMergeBoutsInSameTrials import filterLatencyAndMergeBoutsInSameTrials
  filterLatencyAndMergeBoutsInSameTrials(args.nameOfExperiment, args.minFrameNumberBoutStart, args.maxFrameNumberBoutStart, args.calculationMethod,
                                         paths.getDefaultZZoutputFolder(), args.dropDuplicates)

def launchActiveLearning(args):
  from zebrazoom.otherScripts.launchActiveLearning import launchActiveLearning
  launchActiveLearning()

def launchOptimalClusterNumberSearch(args):
  from zebrazoom.otherScripts.launchOptimalClusterNumberSearch import launchOptimalClusterNumberSearch
  launchOptimalClusterNumberSearch()

def launchReapplyClustering(args):
  from zebrazoom.otherScripts.launchReapplyClustering import launchReapplyClustering
  launchReapplyClustering()

def createSmallValidationVideosForFlagged(args):
  from zebrazoom.code.createValidationVideo import createSmallValidationVideosForFlagged
  createSmallValidationVideosForFlagged(args.videoName.rstrip(r'\/'), args.offset)

def alternativeKinematicParameterCalculation(args):
  from zebrazoom.otherScripts.alternativeKinematicParameterCalculation import alternativeKinematicParameterCalculation
  alternativeKinematicParameterCalculation(args)

def exit(args):
  from PyQt5.QtCore import QTimer
  from zebrazoom.GUIAllPy import ZebraZoomApp
  app = ZebraZoomApp(sys.argv)
  QTimer.singleShot(0, app.window.close)
  sys.exit(app.exec())

def runVideoAnalysis(args):
  print("The data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
  from zebrazoom.zebraZoomVideoAnalysis import ZebraZoomVideoAnalysis

  if args.useGUI:
    try:
      from zebrazoom.GUIAllPy import PlainApplication
      app = PlainApplication(sys.argv)
    except ImportError:
      args.useGUI = False
      print("GUI not available")
  __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
  ZebraZoomVideoAnalysis(args.pathToVideo, args.videoName, args.videoExt, args.configFile, args.hyperparameters, useGUI=args.useGUI).run()
