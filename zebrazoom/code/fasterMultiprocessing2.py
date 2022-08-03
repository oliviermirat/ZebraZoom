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
import time
import zebrazoom.code.util as util

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.getMidline import getMidline
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.findTailExtremete import findTailExtremete
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTheTwoSides import findTheTwoSides
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findBodyContour import findBodyContour
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.Rotate import Rotate
from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle

from zebrazoom.code.trackingFolder.refactoredCode2022.findCenterByIterativelyDilating import findCenterByIterativelyDilating
from zebrazoom.code.trackingFolder.refactoredCode2022.headingCompute import computeHeading2
from zebrazoom.code.trackingFolder.refactoredCode2022.findTheTwoSides2 import findTheTwoSides2
from zebrazoom.code.trackingFolder.refactoredCode2022.identitiesLinkage import findOptimalIdCorrespondance, switchIdentities

from zebrazoom.code.updateBackgroundAtInterval import updateBackgroundAtInterval

def fasterMultiprocessing2(videoPath, background, wellPositions, output, hyperparameters, videoName):
  
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
  # if hyperparameters["eyeTracking"]:
    # trackingEyesAllAnimalsList   = []
  # else:
    # trackingEyesAllAnimals = 0
  trackingDataList               = []
  
  # if not(hyperparameters["nbAnimalsPerWell"] > 1) and not(hyperparameters["headEmbeded"]) and (hyperparameters["findHeadPositionByUserInput"] == 0) and (hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
    # trackingProbabilityOfGoodDetectionList = []
  # else:
    # trackingProbabilityOfGoodDetectionList = 0
  # trackingProbabilityOfGoodDetectionList = []
  
  for wellNumber in range(0, hyperparameters["nbWells"]):
    trackingHeadTailAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2)))
    trackingHeadingAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1)))
    # if hyperparameters["eyeTracking"]:
      # trackingEyesAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, 8)))
    # trackingProbabilityOfGoodDetectionList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1)))
  
  # if hyperparameters["backgroundSubtractorKNN"]:
    # fgbg = cv2.createBackgroundSubtractorKNN()
    # for i in range(0, min(lastFrame - 1, 500), int(min(lastFrame - 1, 500) / 10)):
      # cap.set(1, min(lastFrame - 1, 500) - i)
      # ret, frame = cap.read()
      # fgmask = fgbg.apply(frame)
    # cap.release()
    # cap = zzVideoReading.VideoCapture(videoPath)
  
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
    
      # if hyperparameters["backgroundSubtractorKNN"]:
        # frame = fgbg.apply(frame)
        # frame = 255 - frame
      
      for wellNumber in range(0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"], hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
        
        minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
        xtop = wellPositions[wellNumber]['topLeftX']
        ytop = wellPositions[wellNumber]['topLeftY']
        lenX = wellPositions[wellNumber]['lengthX']
        lenY = wellPositions[wellNumber]['lengthY']
        # if hyperparameters["backgroundSubtractorKNN"]:
          # grey = frame
        # else:
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
        initialCurFrame = curFrame.copy()
        # if not(hyperparameters["backgroundSubtractorKNN"]):
        back = background[ytop:ytop+lenY, xtop:xtop+lenX]
        putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
        curFrame[putToWhite] = 255
        # else:
          # hyperparameters["paramGaussianBlur"] = int(math.sqrt(cv2.countNonZero(255 - curFrame) / hyperparameters["nbAnimalsPerWell"]) / 2) * 2 + 1
        # if hyperparameters["paramGaussianBlur"]:
          # blur = cv2.GaussianBlur(curFrame, (hyperparameters["paramGaussianBlur"], hyperparameters["paramGaussianBlur"]),0)
        # else:
          # blur = curFrame
        headPositionFirstFrame = 0
        
        ret, thresh1 = cv2.threshold(curFrame.copy(), 254, 255, cv2.THRESH_BINARY)
        
        contours, hierarchy = cv2.findContours(thresh1,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        areas = np.array([cv2.contourArea(contour) for contour in contours])
        
        maxIndexes = []
        for numFish in range(0, hyperparameters["nbAnimalsPerWell"]):
          maxArea = -1
          maxInd  = -1
          for idx, area in enumerate(areas):
            if area > maxArea and area > hyperparameters["minAreaBody"] and area < hyperparameters["maxAreaBody"]:
              maxArea = area
              maxInd  = idx
          areas[maxInd] = -1
          if maxInd != -1:
            maxIndexes.append(maxInd)
        
        for animal_Id, idx in enumerate(maxIndexes):
          bodyContour = contours[idx]
          M = cv2.moments(bodyContour)
          if M['m00']:
            # x = int(M['m10']/M['m00'])
            # y = int(M['m01']/M['m00'])
            # headPosition = [x, y]
            headPosition = findCenterByIterativelyDilating(bodyContour.copy(), len(curFrame[0]), len(curFrame))
            
            trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-firstFrame][0][0] = headPosition[0]
            trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-firstFrame][0][1] = headPosition[1]
            
            heading = computeHeading2(bodyContour.copy(), len(curFrame[0]), len(curFrame), headPosition, hyperparameters)
            
            trackingHeadingAllAnimalsList[wellNumber][animal_Id, i-firstFrame] = heading
            
            if hyperparameters["trackTail"] == 1 :
              
              res = findTheTwoSides2(headPosition, bodyContour, curFrame, hyperparameters, heading)
              
              # Finding tail extremity
              rotatedContour = bodyContour.copy()
              rotatedContour = Rotate(rotatedContour,int(headPosition[0]),int(headPosition[1]),heading,curFrame)
              debugAdv = False
              
              [MostCurvyIndex, distance2] = findTailExtremete(rotatedContour, bodyContour, headPosition[0], int(res[0]), int(res[1]), debugAdv, curFrame, hyperparameters["tailExtremityMaxJugeDecreaseCoeff"], hyperparameters)
              
              # Getting Midline
              if hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 0:
                tail = getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, curFrame, nbTailPoints-1, distance2, debugAdv, hyperparameters, nbTailPoints)
              else:
                tail = getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, curFrame, nbTailPoints, distance2, debugAdv, hyperparameters, nbTailPoints)
                tail = np.array([tail[0][1:len(tail[0])]])
              tail = np.insert(tail, 0, headPosition, axis=1)
              trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-firstFrame] = tail
        
        # Eye tracking for frame i
        # if hyperparameters["eyeTracking"]:
          # trackingEyesAllAnimalsList[wellNumber] = eyeTracking(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingEyesAllAnimalsList[wellNumber])
        
        correspondance = findOptimalIdCorrespondance(trackingHeadTailAllAnimalsList, wellNumber, animal_Id, i, firstFrame)
        
        [trackingHeadTailAllAnimalsList, trackingHeadingAllAnimalsList] = switchIdentities(correspondance, trackingHeadTailAllAnimalsList, trackingHeadingAllAnimalsList, wellNumber, animal_Id, i, firstFrame)
        
        debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber], curFrame, hyperparameters)
        
        if hyperparameters["updateBackgroundAtInterval"]:
          background = updateBackgroundAtInterval(i, hyperparameters, background, wellPositions, wellNumber, initialCurFrame, firstFrame, trackingHeadTailAllAnimalsList[wellNumber], initialCurFrame)
        
        if hyperparameters["freqAlgoPosFollow"]:
          if i % hyperparameters["freqAlgoPosFollow"] == 0:
            print("Tracking at frame", i)
        
    # if hyperparameters["adjustFreelySwimTracking"] == 1:
      # i, widgets = adjustFreelySwimTrackingParams(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters, widgets)
    # else:

    i = i + 1
    
  for wellNumber in range(0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"], hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
    
    # if hyperparameters["postProcessMultipleTrajectories"]:
      # [trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingEyesAllAnimals] = postProcessMultipleTrajectories(trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], [], trackingProbabilityOfGoodDetectionList[wellNumber], hyperparameters, wellPositions)
    
    trackingDataList.append([trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0])
  
  wellNumberBeginLoop = 0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"]
  for wellNumber in range(wellNumberBeginLoop, hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
    parameters = extractParameters(trackingDataList[wellNumber-wellNumberBeginLoop], wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.append([wellNumber,parameters,[]])
  
  return output
