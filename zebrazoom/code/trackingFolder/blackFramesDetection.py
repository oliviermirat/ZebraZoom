import numpy as np
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTrackingTeresaNicolson import getMeanOfImageOverVideo

def getThresForBlackFrame(hyperparameters, videoPath):
  threshForBlackFrames = 0
  if hyperparameters["headEmbededTeresaNicolson"] == 1:
    imagesMeans = getMeanOfImageOverVideo(videoPath)
    threshForBlackFrames = imagesMeans * 0.8 #0.75
  return threshForBlackFrames

def savingBlackFrames(hyperparameters, videoName, output):
  if hyperparameters["headEmbededTeresaNicolson"] == 1:
    if hyperparameters["noBoutsDetection"] == 1:
      f = open(hyperparameters["outputFolder"] + videoName + '/blackFrames_' + videoName + '.csv', "a")
      for k in range(1,len(output[0])):
        if np.sum(output[0, k]) == 0:
          output[0, k] = output[0, k-1]
          f.write(str(k)+'\n')
      f.close()
