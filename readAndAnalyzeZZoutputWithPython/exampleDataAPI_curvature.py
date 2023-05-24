import zebrazoom.dataAPI as dataAPI

videoName = "headEmbeddedZebrafishLarva_2023_05_23-16_01_25"  # this will use the latest results file, to use a specific one, provide the full name, e.g. "headEmbeddedZebrafishLarva_2023_05_23-16_01_25"
numWell   = 0
numAnimal = 0

fpsAndPixelSizeSavedInConfigurationFile = True

if fpsAndPixelSizeSavedInConfigurationFile:
  [videoFPS, videoPixelSize] = dataAPI.getFPSandPixelSize(videoName)
else:
  # This would be necessary if videoFPS and videoPixelSize had not already been set in the configuration file before running the tracking
  dataAPI.setFPSandPixelSize(videoName, 300, 0.01)

# Retriving and plotting curvature "per bout"

numBout = 0

[curvatureValues, xTimeValues, yDistanceAlongTheTail] = dataAPI.getCurvaturePerBout(videoName, numWell, numAnimal, numBout)

curvatureValues = dataAPI.applyMedianFilterOnCurvature(curvatureValues, 5)

dataAPI.plotCurvatureYaxisApproximate(curvatureValues, xTimeValues, yDistanceAlongTheTail, videoFPS, videoPixelSize)

dataAPI.plotCurvatureYaxisExact(curvatureValues, xTimeValues, yDistanceAlongTheTail, videoFPS, videoPixelSize)

# Retriving and plotting curvature "per time interval"

startTimeInSeconds = 0.4
endTimeInSeconds   = 6

[curvatureValues, xTimeValues, yDistanceAlongTheTail] = dataAPI.getCurvaturePerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds)

dataAPI.plotCurvatureYaxisApproximate(curvatureValues, xTimeValues, yDistanceAlongTheTail, videoFPS, videoPixelSize)

dataAPI.plotCurvatureYaxisExact(curvatureValues, xTimeValues, yDistanceAlongTheTail, videoFPS, videoPixelSize)
