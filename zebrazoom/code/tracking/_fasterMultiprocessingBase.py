import cv2
import numpy as np
import queue
import os

from ._baseZebraZoom import BaseZebraZoomTrackingMethod


class BaseFasterMultiprocessing(BaseZebraZoomTrackingMethod):
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._videoName = os.path.splitext(os.path.basename(videoPath))[0]
    self._background = None
    self._hyperparameters = hyperparameters
    self._wellPositions = wellPositions
    self._firstWell = 0 if self._hyperparameters["onlyTrackThisOneWell"] == -1 else self._hyperparameters["onlyTrackThisOneWell"]
    self._lastWell = self._hyperparameters["nbWells"] - 1 if self._hyperparameters["onlyTrackThisOneWell"] == -1 else self._hyperparameters["onlyTrackThisOneWell"]
    self._auDessusPerAnimalIdList = None
    self._firstFrame = self._hyperparameters["firstFrame"]
    self._lastFrame = self._hyperparameters["lastFrame"]
    self._nbTailPoints = self._hyperparameters["nbTailPoints"]

    self._trackingHeadTailAllAnimalsList = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2))
                                            for _ in range(self._hyperparameters["nbWells"])]
    self._trackingHeadingAllAnimalsList = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1))
                                           for _ in range(self._hyperparameters["nbWells"])]


  def _detectMovementWithRawVideoInsideTracking(self, i, grey, previousFrames):
    if previousFrames is None:
      previousFrames = queue.Queue(self._hyperparameters["frameGapComparision"])
      # previousXYCoords = queue.Queue(self._hyperparameters["frameGapComparision"])
      self._auDessusPerAnimalIdList = [[np.zeros((self._lastFrame-self._firstFrame+1, 1)) for nbAnimalsPerWell in range(0, self._hyperparameters["nbAnimalsPerWell"])]
                                       for wellNumber in range(self._hyperparameters["nbWells"])]
    halfDiameterRoiBoutDetect = self._hyperparameters["halfDiameterRoiBoutDetect"]
    if previousFrames.full():
      previousFrame   = previousFrames.get()
      curFrame        = grey.copy()
      for wellNumber in range(0 if self._hyperparameters["onlyTrackThisOneWell"] == -1 else self._hyperparameters["onlyTrackThisOneWell"], self._hyperparameters["nbWells"] if self._hyperparameters["onlyTrackThisOneWell"] == -1 else self._hyperparameters["onlyTrackThisOneWell"] + 1):
        for animal_Id in range(self._hyperparameters["nbAnimalsPerWell"]):
          # previousXYCoord = previousXYCoords.get()
          headX = self._trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-self._firstFrame][0][0]
          headY = self._trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-self._firstFrame][0][1]
          xmin = headX - self._hyperparameters["halfDiameterRoiBoutDetect"]
          ymin = headY - self._hyperparameters["halfDiameterRoiBoutDetect"]
          xmax = xmin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
          ymax = ymin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
          lenX = self._wellPositions[wellNumber]['lengthX']
          lenY = self._wellPositions[wellNumber]['lengthY']
          if xmin < 0:
            xmin = 0
          if ymin < 0:
            ymin = 0
          if xmax > lenX - 1:
            xmax = lenX - 1
          if ymax > lenY - 1:
            ymax = lenY - 1
          if ymax < ymin:
            ymax = ymin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
          if xmax < xmin:
            xmax = xmin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
          if ( (xmin > lenX - 1) or (xmax < 0) ):
            xmin = 0
            xmax = 0 + lenX - 1
          if ( (ymin > lenY - 1) or (ymax < 0) ):
            ymin = 0
            ymax = 0 + lenY - 1
          xmin = int(xmin + self._wellPositions[wellNumber]['topLeftX'])
          xmax = int(xmax + self._wellPositions[wellNumber]['topLeftX'])
          ymin = int(ymin + self._wellPositions[wellNumber]['topLeftY'])
          ymax = int(ymax + self._wellPositions[wellNumber]['topLeftY'])
          # img22       = img2[ymin:ymax, xmin:xmax]
          # imgFuture22 = imgFuture2[ymin:ymax, xmin:xmax]
          # maxX = min(len(previousFrame[0]), len(curFrame[0]))
          # maxY = min(len(previousFrame), len(curFrame))
          # print("Av: aaa:", len(previousFrame))
          # print("Av: bbb:", len(previousFrame[0]))
          # print("1Av: aaa:", len(grey))
          # print("1Av: bbb:", len(grey[0]))
          subPreviousFrame = previousFrame[ymin:ymax, xmin:xmax].copy()
          subCurFrame      = curFrame[ymin:ymax, xmin:xmax].copy()
          # print("Aft: aaa:", len(previousFrame))
          # print("Aft: bbb:", len(previousFrame[0]))
          # if i > 250 and wellNumber == 3:
            # print("wellNumber:", wellNumber, "; headX, headY:", headX, headY, "; xmin, xmax, ymin, ymax:", xmin, xmax, ymin, ymax)
            # print("aaa:", len(previousFrame))
            # print("bbb:", len(previousFrame[0]))
            # self._debugFrame(subPreviousFrame, title='subPreviousFrame' + str(wellNumber))
            # self._debugFrame(subCurFrame,      title='subCurFrame' + str(wellNumber))

          # Possible optimization in the future: refine the ROI based on halfDiameterRoiBoutDetect !!!
          res = cv2.absdiff(subPreviousFrame, subCurFrame)
          ret, res = cv2.threshold(res,self._hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)
          totDiff = cv2.countNonZero(res)

          if totDiff > self._hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
            self._auDessusPerAnimalIdList[wellNumber][animal_Id][i-self._firstFrame] = 1
          else:
            self._auDessusPerAnimalIdList[wellNumber][animal_Id][i-self._firstFrame] = 0
    else:
      for wellNumber in range(0 if self._hyperparameters["onlyTrackThisOneWell"] == -1 else self._hyperparameters["onlyTrackThisOneWell"], self._hyperparameters["nbWells"] if self._hyperparameters["onlyTrackThisOneWell"] == -1 else self._hyperparameters["onlyTrackThisOneWell"] + 1):
        for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          self._auDessusPerAnimalIdList[wellNumber][animalId][i-self._firstFrame] = 0
    
    previousFrames.put(grey)
    # previousXYCoords.put([xHead, yHead])
  
    return previousFrames
