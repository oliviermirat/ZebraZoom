import argparse
import os
import sys
import multiprocessing
multiprocessing.freeze_support()  # documentation mistakenly states this is required only on Windows; it's also required on Mac and does nothing on Linux

import zebrazoom.code.paths as paths

import zebrazoom._subcommands as subcommands


def _ensureFolderPermissions():
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
  if not errors:
    return
  errorMessage = "Some of the folders required by ZebraZoom are missing and could not be created:\n" \
                 "%s\n\nZebraZoom cannot work without these folders, please make sure you have adequate " \
                 "write permissions or try an alternative installation method." % '\n'.join(errors)
  try:
    from PyQt5.QtWidgets import QMessageBox
    from zebrazoom.GUIAllPy import PlainApplication
    app = PlainApplication(sys.argv)
    QMessageBox.critical(None, "Required folders missing", errors)
  except ImportError:
    print(errors)
  sys.exit(1)


def _createLegacyVideoAnalysisParser():
  parser = argparse.ArgumentParser(prog=None if getattr(sys, 'frozen', False) else 'python -m zebrazoom',
                                   epilog='Text after help')
  parser.set_defaults(subcommand='runVideoAnalysis')
  parser.add_argument('--use-gui', action='store_true', dest='useGUI', help='Whether to use GUI.')
  parser.add_argument('pathToVideo', help='Help for pathToVideo')
  parser.add_argument('videoName', help='Help for videoName')
  parser.add_argument('videoExt', help='Help for videoExt')
  parser.add_argument('configFile', help='Help for configFile')
  parser.add_argument('hyperparameters', nargs='*', help='Help for hyperparameters')
  return parser


def _createParser():
  parser = argparse.ArgumentParser(prog=None if getattr(sys, 'frozen', False) else 'python -m zebrazoom',
                                   description='Text before help',
                                   epilog='Text after help')
  subparsers = parser.add_subparsers(dest='subcommand', help='Help message for subcommand')
  subparsers.default = 'launchZebraZoom'

  subparsers.add_parser('selectZZoutput', help='Help for selectZZoutput')

  for subcommand in ('getTailExtremityFirstFrame', 'recreateSuperStruct'):
    subparser = subparsers.add_parser(subcommand, help=f'Help for {subcommand}')
    subparser.add_argument('pathToVideo', help='Help for pathToVideo')
    subparser.add_argument('videoName', help='Help for videoName')
    subparser.add_argument('videoExt', help='Help for videoExt')
    subparser.add_argument('configFile', help='Help for configFile')
    subparser.add_argument('hyperparameters', nargs=argparse.REMAINDER, help='Help for hyperparameters')

  subparser = subparsers.add_parser('convertSeqToAvi', help='Help for convertSeqToAvi', description='Description for convertSeqToAvi')
  subparser.add_argument('path', help='Help for path')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('codec', help='Help for codec', nargs='?', default='HFYU')
  subparser.add_argument('lastFrame', help='Help for lastFrame', type=int, nargs='?', default=-1)

  subparser = subparsers.add_parser('convertSeqToAviThenLaunchTracking', help='Help for convertSeqToAviThenLaunchTracking')
  subparser.add_argument('path', help='Help for path')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('configFile', help='Help for configFile')
  subparser.add_argument('codec', help='Help for codec', nargs='?', default='HFYU')
  subparser.add_argument('lastFrame', help='Help for lastFrame', type=int, nargs='?', default=-1)
  subparser.add_argument('hyperparameters', nargs=argparse.REMAINDER, help='Help for hyperparameters')

  subparser = subparsers.add_parser('DL_createMask', help='Help for DL_createMask')
  subparser.add_argument('pathToImgFolder', help='Help for pathToImgFolder')

  subparser = subparsers.add_parser('dataPostProcessing', help='Help for dataPostProcessing')
  postProcessingSubparsers = subparser.add_subparsers(dest='subcommand', help='Help message for postProcessingSubcommand')

  subparser = postProcessingSubparsers.add_parser('sleepVsMoving', help='Help for sleepVsMoving')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('speedThresholdForMoving', help='Help for speedThresholdForMoving', type=float)
  subparser.add_argument('notMovingNumberOfFramesThresholdForSleep', help='Help for notMovingNumberOfFramesThresholdForSleep', type=int)
  subparser.add_argument('maxDistBetweenTwoPointsInsideSleepingPeriod', help='Help for maxDistBetweenTwoPointsInsideSleepingPeriod', type=float, nargs='?', default=-1)
  subparser.add_argument('specifiedStartTime', help='Help for specifiedStartTime', nargs='?', default=0)
  subparser.add_argument('distanceTravelledRollingMedianFilter', help='Help for distanceTravelledRollingMedianFilter', type=int, nargs='?', default=0)
  subparser.add_argument('videoPixelSize', help='Help for videoPixelSize', type=float, nargs='?', default=-1)
  subparser.add_argument('videoFPS', help='Help for videoFPS', type=float, nargs='?', default=-1)

  subparser = postProcessingSubparsers.add_parser('firstSleepingTimeAfterSpecifiedTime', help='Help for firstSleepingTimeAfterSpecifiedTime')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('specifiedTime', help='Help for specifiedTime')
  subparser.add_argument('wellNumber', help='Help for wellNumber')

  subparser = postProcessingSubparsers.add_parser('numberOfSleepingAndMovingTimesInTimeRange', help='Help for numberOfSleepingAndMovingTimesInTimeRange')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('specifiedStartTime', help='Help for specifiedStartTime')
  subparser.add_argument('specifiedEndTime', help='Help for specifiedEndTime')
  subparser.add_argument('wellNumber', help='Help for wellNumber')

  subparser = postProcessingSubparsers.add_parser('numberOfSleepBoutsInTimeRange', help='Help for numberOfSleepBoutsInTimeRange')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('minSleepLenghtDurationThreshold', help='Help for minSleepLenghtDurationThreshold', type=int)
  subparser.add_argument('wellNumber', help='Help for wellNumber', nargs='?', default='-1')
  subparser.add_argument('specifiedStartTime', help='Help for specifiedStartTime', nargs='?', default=-1)
  subparser.add_argument('specifiedEndTime', help='Help for specifiedEndTime', nargs='?', default=-1)

  subparser = postProcessingSubparsers.add_parser('calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshod', help='Help for calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshod')
  subparser.add_argument('experimentName', help='Help for experimentName')
  subparser.add_argument('thresholdInDegrees', help='Help for thresholdInDegrees', type=int)

  subparser = postProcessingSubparsers.add_parser('kinematicParametersAnalysis', help='Help for kinematicParametersAnalysis')
  subparser.add_argument('args', nargs='*')

  subparser = postProcessingSubparsers.add_parser('kinematicParametersAnalysisWithMedianPerGenotype', help='Help for kinematicParametersAnalysisWithMedianPerGenotype')
  subparser.add_argument('args', nargs='*')

  subparser = postProcessingSubparsers.add_parser('clusteringAnalysis', help='Help for clusteringAnalysis')
  subparser.add_argument('args', nargs='*')

  subparser = postProcessingSubparsers.add_parser('clusteringAnalysisPerFrame', help='Help for clusteringAnalysisPerFrame')
  subparser.add_argument('args', nargs='*')

  subparser = postProcessingSubparsers.add_parser('kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection', help='Help for kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection')
  subparser.add_argument('args', nargs='*')

  subparser = subparsers.add_parser('visualizeMovingAndSleepingTime', help='Help for visualizeMovingAndSleepingTime')
  subparser.add_argument('movingOrSleeping', help='Help message for movingOrSleeping', choices=('movingTime', 'sleepingTime'))
  subparser.add_argument('videoName', help='Help for videoName')

  subparser = subparsers.add_parser('createDistanceBetweenFramesExcelFile', help='Help for createDistanceBetweenFramesExcelFile')
  subparser.add_argument('videoFPS', help='Help for videoFPS', type=float, nargs='?', default=1)
  subparser.add_argument('videoPixelSize', help='Help for videoPixelSize', type=float, nargs='?', default=1)

  subparser = subparsers.add_parser('createDistanceSpeedHeadingDeltaHeadingExcelFile', help='Help for createDistanceSpeedHeadingDeltaHeadingExcelFile')
  subparser.add_argument('videoFPS', help='Help for videoFPS', type=float, nargs='?', default=1)
  subparser.add_argument('videoPixelSize', help='Help for videoPixelSize', type=float, nargs='?', default=1)

  subparser = subparsers.add_parser('removeLargeInstantaneousDistanceData', help='Help for removeLargeInstantaneousDistanceData')
  subparser.add_argument('maxDistance', help='Help for maxDistance', type=float, nargs='?', default=1)

  subparser = subparsers.add_parser('filterLatencyAndMergeBoutsInSameTrials', help='Help for filterLatencyAndMergeBoutsInSameTrials')
  subparser.add_argument('nameOfExperiment', help='Help message for nameOfExperiment')
  subparser.add_argument('minFrameNumberBoutStart', help='Help for minFrameNumberBoutStart', type=int)
  subparser.add_argument('maxFrameNumberBoutStart', help='Help for maxFrameNumberBoutStart', type=int)
  subparser.add_argument('calculationMethod', help='Help for calculationMethod', nargs='?', default='median', choices=('mean', 'median'))
  subparser.add_argument('dropDuplicates', help='Help for dropDuplicates', nargs='?', type=int, default=0, choices=(0, 1))

  subparser = subparsers.add_parser('otherScripts', help='Help for otherScripts')
  otherScriptsSubparsers = subparser.add_subparsers(dest='subcommand', help='Help message for otherScripts subcommand')

  subparser = otherScriptsSubparsers.add_parser('launchActiveLearning', help='Help for launchActiveLearning')

  subparser = otherScriptsSubparsers.add_parser('launchOptimalClusterNumberSearch', help='Help for launchOptimalClusterNumberSearch')

  subparser = otherScriptsSubparsers.add_parser('launchReapplyClustering', help='Help for launchReapplyClustering')

  subparser = subparsers.add_parser('createSmallValidationVideosForFlagged', help='Help for createSmallValidationVideosForFlagged')
  subparser.add_argument('videoName', help='Help for videoName')
  subparser.add_argument('offset', help='Help for offset', type=int)

  subparser = otherScriptsSubparsers.add_parser('alternativeKinematicParameterCalculation', help='Help for alternativeKinematicParameterCalculation')
  subparser.add_argument('nameOfExperiment', help='Help message for nameOfExperiment')

  subparser = subparsers.add_parser('exit', help='Run ZebraZoom and immediately exit.')

  if len(sys.argv) > 1 and sys.argv[1] not in subparsers.choices and os.path.exists(sys.argv[1]):
    # XXX: add this format to help somewhere?
    # the first argument is a path, use the old generic format for running video analysis
    return _createLegacyVideoAnalysisParser()

  return parser


if __name__ == '__main__':
  _ensureFolderPermissions()
  args = _createParser().parse_args()
  getattr(subcommands, args.subcommand)(args)
