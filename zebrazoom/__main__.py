if __name__ == '__main__':

  import sys
  import multiprocessing
  multiprocessing.freeze_support()  # documentation mistakenly states this is required only on Windows; it's also required on Mac and does nothing on Linux

  import os
  import zebrazoom.code.paths as paths

  from zebrazoom.code.vars import getGlobalVariables
  globalVariables = getGlobalVariables()

  requiredFolders = (paths.getDefaultZZoutputFolder(), paths.getConfigurationFolder(),
                     os.path.join(paths.getDataAnalysisFolder(), 'data'),
                     os.path.join(paths.getDataAnalysisFolder(), 'experimentOrganizationExcel'),
                     os.path.join(paths.getDataAnalysisFolder(), 'resultsClustering'),
                     os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'))
  errors = []
  for folder in requiredFolders:
    try:
      os.makedirs(folder, exist_ok=True)
    except OSError:
      errors.append(folder)
  if errors:
    errorMessage = "Some of the folders required by ZebraZoom are missing and could not be created:\n" \
                   "%s\n\nZebraZoom cannot work without these folders, please make sure you have adequate " \
                   "write permissions or try an alternative installation method." % '\n'.join(errors)

  if len(sys.argv) == 1:

    if errors:
      from PyQt5.QtWidgets import QMessageBox
      from zebrazoom.GUIAllPy import PlainApplication
      app = PlainApplication(sys.argv)
      QMessageBox.critical(None, "Required folders missing", errorMessage)
      sys.exit(1)
    from zebrazoom.GUIAllPy import ZebraZoomApp
    print("The data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
    app = ZebraZoomApp(sys.argv)
    sys.exit(app.exec())

  else:

    if errors:
      print(errorMessage)
      sys.exit(1)

    if sys.argv[1] == "selectZZoutput" or sys.argv[1] == "--exit":
      from zebrazoom.GUIAllPy import ZebraZoomApp
      app = ZebraZoomApp(sys.argv)

    if sys.argv[1] == "selectZZoutput":

      print("The data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
      app.askForZZoutputLocation()
      sys.exit(app.exec())

    elif sys.argv[1] == "getTailExtremityFirstFrame":

      pathToVideo = sys.argv[2]
      videoName   = sys.argv[3]
      videoExt    = sys.argv[4]
      configFile  = sys.argv[5]
      argv        = sys.argv
      argv.pop(0)
      from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      getTailExtremityFirstFrame(pathToVideo, videoName, videoExt, configFile, argv)


    elif sys.argv[1] == "recreateSuperStruct":

      pathToVideo = sys.argv[2]
      videoName   = sys.argv[3]
      videoExt    = sys.argv[4]
      configFile  = sys.argv[5]
      argv        = sys.argv
      argv.pop(0)
      from zebrazoom.recreateSuperStruct import recreateSuperStruct
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      recreateSuperStruct(pathToVideo, videoName, videoExt, configFile, argv)


    elif sys.argv[1] == "convertSeqToAvi":

      from zebrazoom.videoFormatConversion.seq_to_avi import sqb_convert_to_avi
      path      = sys.argv[2]
      videoName = sys.argv[3]
      codec     = sys.argv[4] if len(sys.argv) >= 5 else 'HFYU'
      lastFrame = int(sys.argv[5]) if len(sys.argv) >= 6 else -1
      sqb_convert_to_avi(path, videoName, codec, lastFrame)


    elif sys.argv[1] == "convertSeqToAviThenLaunchTracking":

      from zebrazoom.videoFormatConversion.seq_to_avi import sqb_convert_to_avi
      from zebrazoom.mainZZ import mainZZ
      from pathlib import Path
      import time
      path       = sys.argv[2]
      videoName  = sys.argv[3]
      configFile = sys.argv[4]
      codec      = sys.argv[5] if len(sys.argv) >= 6 else 'HFYU'
      lastFrame  = int(sys.argv[6]) if len(sys.argv) >= 7 else -1
      argv2      = sys.argv.copy()
      del argv2[1:2]
      argv2.insert(3, 'avi')
      del argv2[5:7]
      path2      = Path(path).parent
      print("Launching the convertion from seq to avi")
      sqb_convert_to_avi(path, videoName, codec, lastFrame)
      print("small break start")
      time.sleep(2)
      print("Launching the tracking, the data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      mainZZ(path2, videoName, 'avi', configFile, argv2, useGUI=False)


    elif sys.argv[1] == "DL_createMask":

      from zebrazoom.code.deepLearningFunctions.labellingFunctions import createMask
      pathToImgFolder = sys.argv[2]
      if not(os.path.exists(pathToImgFolder)):
        pathToImgFolder = os.path.join(paths.getDefaultZZoutputFolder(), sys.argv[2], 'PNGImages')
      createMask(pathToImgFolder)


    elif sys.argv[1] == "dataPostProcessing":

      if sys.argv[2] == "sleepVsMoving":
        from zebrazoom.code.dataPostProcessing.findSleepVsMoving import calculateSleepVsMovingPeriods
        pathToZZoutput = paths.getDefaultZZoutputFolder()
        videoName      = sys.argv[3]
        speedThresholdForMoving = float(sys.argv[4])
        notMovingNumberOfFramesThresholdForSleep = int(sys.argv[5])
        maxDistBetweenTwoPointsInsideSleepingPeriod = float(sys.argv[6]) if len(sys.argv) >= 7 else -1
        if len(sys.argv) >= 8:
         specifiedStartTime  = sys.argv[7]
        else:
          specifiedStartTime = 0
        if len(sys.argv) >= 9:
          distanceTravelledRollingMedianFilter = int(sys.argv[8])
        else:
          distanceTravelledRollingMedianFilter = 0
        if len(sys.argv) >= 11:
          videoPixelSize = float(sys.argv[9])
          videoFPS = float(sys.argv[10])
        else:
          videoPixelSize = -1
          videoFPS = -1
        calculateSleepVsMovingPeriods(pathToZZoutput, videoName, speedThresholdForMoving, notMovingNumberOfFramesThresholdForSleep, maxDistBetweenTwoPointsInsideSleepingPeriod, specifiedStartTime, distanceTravelledRollingMedianFilter, videoPixelSize, videoFPS)

      if sys.argv[2] == "firstSleepingTimeAfterSpecifiedTime":
        from zebrazoom.code.dataPostProcessing.findSleepVsMoving import firstSleepingTimeAfterSpecifiedTime
        pathToZZoutput = paths.getDefaultZZoutputFolder()
        videoName      = sys.argv[3]
        specifiedTime  = sys.argv[4]
        wellNumber     = sys.argv[5]
        firstSleepingTimeAfterSpecifiedTime(pathToZZoutput, videoName, specifiedTime, wellNumber)

      if sys.argv[2] == "numberOfSleepingAndMovingTimesInTimeRange":
        from zebrazoom.code.dataPostProcessing.findSleepVsMoving import numberOfSleepingAndMovingTimesInTimeRange
        pathToZZoutput     = paths.getDefaultZZoutputFolder()
        videoName          = sys.argv[3]
        specifiedStartTime = sys.argv[4]
        specifiedEndTime   = sys.argv[5]
        wellNumber         = sys.argv[6]
        numberOfSleepingAndMovingTimesInTimeRange(pathToZZoutput, videoName, specifiedStartTime, specifiedEndTime, wellNumber)

      if sys.argv[2] == "numberOfSleepBoutsInTimeRange":
        from zebrazoom.code.dataPostProcessing.findSleepVsMoving import numberOfSleepBoutsInTimeRange
        pathToZZoutput                  = paths.getDefaultZZoutputFolder()
        videoName                       = sys.argv[3]
        minSleepLenghtDurationThreshold = int(sys.argv[4])
        wellNumber                      = sys.argv[5] if len(sys.argv) >= 6 else '-1'
        specifiedStartTime              = sys.argv[6] if len(sys.argv) >= 8 else -1
        specifiedEndTime                = sys.argv[7] if len(sys.argv) >= 8 else -1
        numberOfSleepBoutsInTimeRange(pathToZZoutput, videoName, minSleepLenghtDurationThreshold, wellNumber, specifiedStartTime, specifiedEndTime)

      if sys.argv[2] == "calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshod":
        from zebrazoom.dataAnalysis.postProcessingFromCommandLine.postProcessingFromCommandLine import calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold
        calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold(paths.getRootDataFolder(), sys.argv[3], int(sys.argv[4]))

      if sys.argv[2] == "kinematicParametersAnalysis":
        from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis
        kinematicParametersAnalysis(sys)

      if sys.argv[2] == "kinematicParametersAnalysisWithMedianPerGenotype":
        from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis
        kinematicParametersAnalysis(sys, 1)

      if sys.argv[2] == "clusteringAnalysis":
        from zebrazoom.clusteringAnalysis import clusteringAnalysis
        clusteringAnalysis(sys)

      if sys.argv[2] == "clusteringAnalysisPerFrame":
        from zebrazoom.clusteringAnalysisPerFrame import clusteringAnalysisPerFrame
        clusteringAnalysisPerFrame(sys)

      if sys.argv[2] == "kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection":
        from zebrazoom.kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection import kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection
        kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection(sys)

    elif sys.argv[1] == "visualizeMovingAndSleepingTime":

      from zebrazoom.code.readValidationVideo import readValidationVideo
      import pandas as pd
      df = pd.read_excel(os.path.join(paths.getDefaultZZoutputFolder(), sys.argv[3], "sleepVsMoving_" + sys.argv[3] + ".xlsx"))
      nbWells = int(len(df.columns)/3)

      if sys.argv[2] == "movingTime":

        framesToShow = df[["moving_" + str(i) for i in range(0, nbWells)]].to_numpy()
        readValidationVideo("", sys.argv[3], "", -1, -1, 0, 1, framesToShow)

      elif sys.argv[2] == "sleepingTime":

        framesToShow = df[["sleep_" + str(i) for i in range(0, nbWells)]].to_numpy()
        readValidationVideo("", sys.argv[3], "", -1, -1, 0, 1, framesToShow)

    elif sys.argv[1] == "createDistanceBetweenFramesExcelFile":

      from zebrazoom.dataAnalysis.createCustomDataStructure.createDistanceBetweenFramesExcelFile import createDistanceBetweenFramesExcelFile
      createDistanceBetweenFramesExcelFile(paths.getDefaultZZoutputFolder(), sys.argv) # fps, pixelSize
      

    elif sys.argv[1] == "otherScripts":

      if sys.argv[2] == "launchActiveLearning":

        from zebrazoom.otherScripts.launchActiveLearning import launchActiveLearning
        launchActiveLearning()

      elif sys.argv[2] == "launchOptimalClusterNumberSearch":

        from zebrazoom.otherScripts.launchOptimalClusterNumberSearch import launchOptimalClusterNumberSearch
        launchOptimalClusterNumberSearch()

      elif sys.argv[2] == "launchReapplyClustering":

        from zebrazoom.otherScripts.launchReapplyClustering import launchReapplyClustering
        launchReapplyClustering()

    elif sys.argv[1] == 'createSmallValidationVideosForFlagged':
      from zebrazoom.code.createValidationVideo import createSmallValidationVideosForFlagged
      createSmallValidationVideosForFlagged(sys.argv[2].rstrip(r'\/'), int(sys.argv[3]))
    elif sys.argv[1] == "--exit":
      from PyQt5.QtCore import QTimer
      QTimer.singleShot(0, app.window.close)
      sys.exit(app.exec())
    else:

      print("The data produced by ZebraZoom can be found in the folder: " + paths.getDefaultZZoutputFolder())
      pathToVideo = sys.argv[1]
      videoName   = sys.argv[2]
      videoExt    = sys.argv[3]
      configFile  = sys.argv[4]
      argv        = sys.argv

      from zebrazoom.mainZZ import mainZZ

      try:
        from zebrazoom.GUIAllPy import PlainApplication
        app = PlainApplication(sys.argv)
        useGUI = True
      except ImportError:
        useGUI = False
        print("GUI not available")
      __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
      mainZZ(pathToVideo, videoName, videoExt, configFile, argv, useGUI=useGUI)
