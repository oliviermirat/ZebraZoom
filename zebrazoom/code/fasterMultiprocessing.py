from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.tailTracking import tailTracking
from zebrazoom.code.trackingFolder.eyeTracking.eyeTracking import eyeTracking
from zebrazoom.code.trackingFolder.postProcessMultipleTrajectories import postProcessMultipleTrajectories
from zebrazoom.code.trackingFolder.getImages import getImages
from zebrazoom.code.trackingFolder.debugTracking import debugTracking
from zebrazoom.code.adjustHyperparameters import adjustFreelySwimTrackingParams
import multiprocessing as mp
from multiprocessing import Process
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import numpy as np
import math

def fasterMultiprocessing(videoPath, background, wellPositions, output, hyperparameters, videoName):
  
  cap = zzVideoReading.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  nbTailPoints = hyperparameters["nbTailPoints"]
  
  trackingHeadTailAllAnimalsList = []
  trackingHeadingAllAnimalsList  = []
  if hyperparameters["eyeTracking"]:
    trackingEyesAllAnimalsList   = []
  else:
    trackingEyesAllAnimals = 0
  trackingDataList               = []
  
  if not(hyperparameters["nbAnimalsPerWell"] > 1) and not(hyperparameters["headEmbeded"]) and (hyperparameters["findHeadPositionByUserInput"] == 0) and (hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
    trackingProbabilityOfGoodDetectionList = []
  else:
    trackingProbabilityOfGoodDetectionList = 0
  
  for wellNumber in range(0, hyperparameters["nbWells"]):
    trackingHeadTailAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2)))
    trackingHeadingAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1)))
    if hyperparameters["eyeTracking"]:
      trackingEyesAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, 8)))
    if not(hyperparameters["nbAnimalsPerWell"] > 1) and not(hyperparameters["headEmbeded"]) and (hyperparameters["findHeadPositionByUserInput"] == 0) and (hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
      trackingProbabilityOfGoodDetectionList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1)))
  
  if hyperparameters["backgroundSubtractorKNN"]:
    fgbg = cv2.createBackgroundSubtractorKNN()
    for i in range(0, min(lastFrame - 1, 500), int(min(lastFrame - 1, 500) / 10)):
      cap.set(1, min(lastFrame - 1, 500) - i)
      ret, frame = cap.read()
      fgmask = fgbg.apply(frame)
    cap.release()
    cap = zzVideoReading.VideoCapture(videoPath)
  
  i = firstFrame
  
  if firstFrame:
    cap.set(1, firstFrame)
  
  widgets = None
  while (i < lastFrame + 1):
    
    if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % hyperparameters["freqAlgoPosFollow"] == 0):
      print("Tracking: frame:",i)
      if hyperparameters["popUpAlgoFollow"]:
        from zebrazoom.code.popUpAlgoFollow import prepend

        prepend("Tracking: frame:" + str(i))
    
    if hyperparameters["debugTracking"]:
      print("frame:",i)
      
    ret, frame = cap.read()
    
    if ret:
    
      if hyperparameters["backgroundSubtractorKNN"]:
        frame = fgbg.apply(frame)
        frame = 255 - frame
      
      for wellNumber in range(0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"], hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
        
        if hyperparameters["nbAnimalsPerWell"] == 1 and not(hyperparameters["forceBlobMethodForHeadTracking"]):
          minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
          xtop = wellPositions[wellNumber]['topLeftX']
          ytop = wellPositions[wellNumber]['topLeftY']
          lenX = wellPositions[wellNumber]['lengthX']
          lenY = wellPositions[wellNumber]['lengthY']
          if hyperparameters["backgroundSubtractorKNN"]:
            grey = frame
          else:
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
          if not(hyperparameters["backgroundSubtractorKNN"]):
            back = background[ytop:ytop+lenY, xtop:xtop+lenX]
            putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
            curFrame[putToWhite] = 255
          else:
            hyperparameters["paramGaussianBlur"] = int(math.sqrt(cv2.countNonZero(255 - curFrame) / hyperparameters["nbAnimalsPerWell"]) / 2) * 2 + 1
          if hyperparameters["paramGaussianBlur"]:
            blur = cv2.GaussianBlur(curFrame, (hyperparameters["paramGaussianBlur"], hyperparameters["paramGaussianBlur"]),0)
          else:
            blur = curFrame
          headPositionFirstFrame = 0
          thresh1 = 0
          thresh2 = 0
          gray    = 0
        else:
          [frame2, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = getImages(hyperparameters, 0, videoPath, i, background, wellNumber, wellPositions, frame)
          headPositionFirstFrame = 0
        
        # Head tracking and heading calculation
        
        [trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingProbabilityOfGoodDetectionList[wellNumber],lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingProbabilityOfGoodDetectionList[wellNumber], headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
        
        # Tail tracking for frame i
        if hyperparameters["trackTail"] == 1 :
          threshForBlackFrames = 0
          thetaDiffAccept = 1.2
          lastFirstTheta = 0
          maxDepth = 0
          tailTipFirstFrame = []
          for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
            [trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber]] = tailTracking(animalId, i, firstFrame, videoPath, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber], lastFirstTheta, maxDepth, tailTipFirstFrame, initialCurFrame.copy(), back)
        
        # Eye tracking for frame i
        if hyperparameters["eyeTracking"]:
          trackingEyesAllAnimalsList[wellNumber] = eyeTracking(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingEyesAllAnimalsList[wellNumber])
        
        debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber], blur, hyperparameters)
        
        if hyperparameters["freqAlgoPosFollow"]:
          if i % hyperparameters["freqAlgoPosFollow"] == 0:
            print("Tracking at frame", i)
        
    if hyperparameters["adjustFreelySwimTracking"] == 1:
      i, widgets = adjustFreelySwimTrackingParams(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters, widgets)
    else:
      i = i + 1
    
  for wellNumber in range(0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"], hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
    
    if hyperparameters["postProcessMultipleTrajectories"]:
      [trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingEyesAllAnimals] = postProcessMultipleTrajectories(trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], [], trackingProbabilityOfGoodDetectionList[wellNumber], hyperparameters, wellPositions)
    
    trackingDataList.append([trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0])
  
  wellNumberBeginLoop = 0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"]
  for wellNumber in range(wellNumberBeginLoop, hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
    parameters = extractParameters(trackingDataList[wellNumber-wellNumberBeginLoop], wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.append([wellNumber,parameters,[]])
  
  return output