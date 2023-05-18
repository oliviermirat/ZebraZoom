import zebrazoom.dataAPI.getCurvaturePerBout as curvaturePerBout
import zebrazoom.dataAPI.getCurvaturePerTimeInterval as curvaturePerTimeInterval
import zebrazoom.dataAPI.plotCurvature as plottingCurvature


def getCurvaturePerBout(videoName, numWell, numAnimal, numBout):
  return curvaturePerBout.getCurvaturePerBout(videoName, numWell, numAnimal, numBout)

def getCurvaturePerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds):
  return curvaturePerTimeInterval.getCurvaturePerTimeInterval(videoName, numWell, numAnimal,  startTimeInSeconds, endTimeInSeconds)

def plotCurvatureYaxisExact(curvatureValues, xTimeValues, yDistanceAlongTail):
  return plottingCurvature.plotCurvatureYaxisExact(curvatureValues, xTimeValues, yDistanceAlongTail)

def plotCurvatureYaxisApproximate(curvatureValues, xTimeValues, yDistanceAlongTail):
  return plottingCurvature.plotCurvatureYaxisApproximate(curvatureValues, xTimeValues, yDistanceAlongTail)
  