import numpy as np
import csv
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
import os
import pickle
import sys
import queue

from zebrazoom.code.extractParameters import extractParameters

from ._base import register_tracking_method
from ._baseZebraZoom import BaseZebraZoomTrackingMethod
from ._eyeTracking import EyeTrackingMixin
from ._getImages import GetImagesMixin
from ._tailTracking import TailTrackingMixin
from ._tailTrackingDifficultBackground import TailTrackingDifficultBackgroundMixin

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()


class Tracking(BaseZebraZoomTrackingMethod, TailTrackingDifficultBackgroundMixin, EyeTrackingMixin, GetImagesMixin, TailTrackingMixin):
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._hyperparameters = hyperparameters
    self._background = None
    self._wellPositions = wellPositions
    self._videoName = os.path.splitext(os.path.basename(videoPath))[0]
    self._auDessusPerAnimalId = None
    self._firstFrame = self._hyperparameters.get("firstFrame", 0) if self._hyperparameters["firstFrameForTracking"] == -1 else self._hyperparameters["firstFrameForTracking"]
    self._lastFrame = self._hyperparameters.get("lastFrame", 0)
    self._nbTailPoints = self._hyperparameters["nbTailPoints"]
    self._headPositionFirstFrame = []
    self._tailTipFirstFrame = []
    self._trackingHeadTailAllAnimals = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2))
    self._trackingHeadingAllAnimals = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1))
    if self._hyperparameters["eyeTracking"]:
      self._trackingEyesAllAnimals = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, 8))
    else:
      self._trackingEyesAllAnimals = 0

    if not(self._hyperparameters["nbAnimalsPerWell"] > 1 or self._hyperparameters["forceBlobMethodForHeadTracking"]) and not(self._hyperparameters["headEmbeded"]) and (self._hyperparameters["findHeadPositionByUserInput"] == 0) and (self._hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
      self._trackingProbabilityOfGoodDetection = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1))
    else:
      self._trackingProbabilityOfGoodDetection = 0

    self.useGUI = True

  def _adjustParameters(self, i, initialCurFrame, frame, frame2, back, widgets):
    return None

  def _addBlackLineToImgSetParameters(self, frame):
    raise ValueError("GUI is required to add black line to image")

  def findTailTipByUserInput(self, frame, frameNumber, wellNumber):
    raise ValueError("GUI is required to select tail tip coordinates, please specify them in advance using the GUI or use --use-gui option")

  def findHeadPositionByUserInput(self, frame, frameNumber, wellNumber):
    raise ValueError("GUI is required to select head coordinates, please specify them in advance using the GUI or use --use-gui option")

  def _getTailTipByFileSaved(self):
    ix = -1
    iy = -1
    inputsFolder = os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName)
    with open(os.path.join(inputsFolder, f'{self._videoName}.csv')) as csv_file:
      csv_reader = csv.reader(csv_file, delimiter=',')
      line_count = 0
      for row in csv_reader:
        if len(row):
          ix = row[0]
          iy = row[1]
    return [int(ix),int(iy)]

  def _getHeadPositionByFileSaved(self):
    ix = -1
    iy = -1
    inputsFolder = os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName)
    with open(os.path.join(inputsFolder, f'{self._videoName}HP.csv')) as csv_file:
      csv_reader = csv.reader(csv_file, delimiter=',')
      line_count = 0
      for row in csv_reader:
        if len(row):
          ix = row[0]
          iy = row[1]
    return [int(ix),int(iy)]

  def _detectMovementWithRawVideoInsideTracking(self, i, xHead, yHead, initialCurFrame):
    previousFrames   = queue.Queue(self._hyperparameters["frameGapComparision"])
    previousXYCoords = queue.Queue(self._hyperparameters["frameGapComparision"])
    self._auDessusPerAnimalId = [np.zeros((self._lastFrame-self._firstFrame+1, 1)) for _ in range(self._hyperparameters["nbAnimalsPerWell"])]
    halfDiameterRoiBoutDetect = self._hyperparameters["halfDiameterRoiBoutDetect"]
    if previousFrames.full():
      previousFrame   = previousFrames.get()
      curFrame        = initialCurFrame.copy()
      previousXYCoord = previousXYCoords.get()
      curXYCoord      = [xHead, yHead]
      if previousXYCoord[0] < curXYCoord[0]:
        previousFrame = previousFrame[:, (curXYCoord[0]-previousXYCoord[0]):]
      elif previousXYCoord[0] > curXYCoord[0]:
        curFrame      = curFrame[:, (previousXYCoord[0]-curXYCoord[0]):]
      if previousXYCoord[1] < curXYCoord[1]:
        previousFrame = previousFrame[(curXYCoord[1]-previousXYCoord[1]):, :]
      elif previousXYCoord[1] > curXYCoord[1]:
        curFrame      = curFrame[(previousXYCoord[1]-curXYCoord[1]):, :]
      maxX = min(len(previousFrame[0]), len(curFrame[0]))
      maxY = min(len(previousFrame), len(curFrame))

      previousFrame = previousFrame[:maxY, :maxX]
      curFrame      = curFrame[:maxY, :maxX]

      # Possible optimization in the future: refine the ROI based on halfDiameterRoiBoutDetect !!!

      res = cv2.absdiff(previousFrame, curFrame)
      ret, res = cv2.threshold(res,self._hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)

      totDiff = cv2.countNonZero(res)
      for animalId in range(self._hyperparameters["nbAnimalsPerWell"]):
        if totDiff > self._hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
          self._auDessusPerAnimalId[animalId][i-self._firstFrame] = 1
        else:
          self._auDessusPerAnimalId[animalId][i-self._firstFrame] = 0
    else:
      self._auDessusPerAnimalId[animalId][i-self._firstFrame] = 0
    previousFrames.put(initialCurFrame)
    previousXYCoords.put([xHead, yHead])

  def _loadDLModel(self):
    # Reloading DL model for tracking with DL
    from zebrazoom.code.deepLearningFunctions.loadDLmodel import loadDLmodel
    return loadDLmodel(self._hyperparameters["trackingDL"], self._hyperparameters["unet"])

  def _trackingDL(self, wellNumber, device, dlModel):
    import torch
    debugPlus = False
    # dicotomySearchOfOptimalBlobArea = self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"] # 500 # 700 # 850
    # applySimpleThresholdOnPredictedMask = self._hyperparameters["applySimpleThresholdOnPredictedMask"] # 230

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']

    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")
    frame_width  = int(cap.get(3))
    frame_height = int(cap.get(4))

    # Performing the tracking on each frame
    applyQuantile = self._hyperparameters["applyQuantileInDLalgo"]
    i = self._firstFrame
    cap.set(1, self._firstFrame)
    if int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
      self._lastFrame = min(self._lastFrame, self._firstFrame + int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
    while (i < self._lastFrame+1):

      if (self._hyperparameters["freqAlgoPosFollow"] != 0) and (i % self._hyperparameters["freqAlgoPosFollow"] == 0):
        print("Tracking: wellNumber:",wellNumber," ; frame:",i)
        if self._hyperparameters["popUpAlgoFollow"]:
          from zebrazoom.code.popUpAlgoFollow import prepend
          prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
      if self._hyperparameters["debugTracking"]:
        print("frame:",i)

      ret, frame = cap.read()
      if applyQuantile:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        quartileChose = 0.03
        lowVal  = int(np.quantile(frame, quartileChose))
        highVal = int(np.quantile(frame, 1 - quartileChose))
        frame[frame < lowVal]  = lowVal
        frame[frame > highVal] = highVal
        frame = frame - lowVal
        mult  = np.max(frame)
        frame = frame * (255/mult)
        frame = frame.astype('uint8')

      if not(ret):
        currentFrameNum = int(cap.get(1))
        while not(ret):
          currentFrameNum = currentFrameNum - 1
          cap.set(1, currentFrameNum)
          ret, frame = cap.read()
          if applyQuantile:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            quartileChose = 0.01
            lowVal  = int(np.quantile(frame, quartileChose))
            highVal = int(np.quantile(frame, 1 - quartileChose))
            frame[frame < lowVal]  = lowVal
            frame[frame > highVal] = highVal
            frame = frame - lowVal
            mult  = np.max(frame)
            frame = frame * (255/mult)
            frame = frame.astype('uint8')

      if applyQuantile:
        grey = frame
      else:
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

      curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]

      if self._hyperparameters["unet"]:

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        imgTorch = torch.from_numpy(curFrame/255)
        imgTorch = imgTorch.unsqueeze(0).unsqueeze(0)
        imgTorch = imgTorch.to(device=device, dtype=torch.float32)

        output = dlModel(imgTorch).cpu()

        import torch.nn.functional as F
        output = F.interpolate(output, (len(curFrame[1]), len(curFrame)), mode='bilinear')
        if dlModel.n_classes > 1:
            mask = output.argmax(dim=1)
        else:
            mask = torch.sigmoid(output) > out_threshold
        thresh2 = mask[0].long().squeeze().numpy()
        thresh2 = thresh2 * 255
        thresh2 = thresh2.astype('uint8')

        thresh3 = thresh2.copy()

        if self._hyperparameters["debugTracking"]:
          self._debugFrame(thresh2, title='After Unet')

        lastFirstTheta = self._headTrackingHeadingCalculation(i, thresh2, thresh2, thresh2, thresh2, self._hyperparameters["erodeSize"], frame_width, frame_height, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection, 0, self._wellPositions[wellNumber]["lengthX"])

        if self._hyperparameters["trackTail"] == 1:
          for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
            self._tailTracking(animalId, i, thresh3, thresh3, thresh3, 0, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, 0, 0, thresh3, 0, wellNumber)

        # Debug functions
        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, curFrame)

      else: # mask rcnn

        oneChannel  = curFrame.tolist()
        oneChannel2 = [[a/255 for a in list] for list in oneChannel]
        imgTorch    = torch.tensor([oneChannel2, oneChannel2, oneChannel2])

        with torch.no_grad():
          prediction = dlModel([imgTorch.to(device)])

        if len(prediction) and len(prediction[0]['masks']):
          thresh = prediction[0]['masks'][0, 0].mul(255).byte().cpu().numpy()
          if debugPlus:
            self._debugFrame(255 - thresh, title="thresh")

          if self._hyperparameters["applySimpleThresholdOnPredictedMask"]:
            ret, thresh2 = cv2.threshold(thresh, self._hyperparameters["applySimpleThresholdOnPredictedMask"], 255, cv2.THRESH_BINARY)
            if self._hyperparameters["simpleThresholdCheckMinForMaxCountour"]:
              contours, hierarchy = cv2.findContours(thresh2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
              maxContourArea = 0
              for contour in contours:
                area = cv2.contourArea(contour)
                if area > maxContourArea:
                  maxContourArea = area
              if maxContourArea < self._hyperparameters["simpleThresholdCheckMinForMaxCountour"]:
                print("maxContour found had a value that's too low (for wellNumber:", wellNumber, ", frame:", i,")")
                countNonZeroTarget = self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"]
                countNonZero       = 0
                low  = 0
                high = 255
                while abs(countNonZero - countNonZeroTarget) > 100 and (high - low) > 1:
                  thresValueToTry = int((low + high) / 2)
                  ret, thresh2 = cv2.threshold(thresh, thresValueToTry, 255, cv2.THRESH_BINARY)
                  countNonZero = cv2.countNonZero(thresh2)
                  if countNonZero > countNonZeroTarget:
                    low = thresValueToTry
                  else:
                    high = thresValueToTry
          else:
            if self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"]:
              countNonZeroTarget = self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"]
              countNonZero       = 0
              low  = 0
              high = 255
              while abs(countNonZero - countNonZeroTarget) > 100 and (high - low) > 1:
                thresValueToTry = int((low + high) / 2)
                ret, thresh2 = cv2.threshold(thresh, thresValueToTry, 255, cv2.THRESH_BINARY)
                countNonZero = cv2.countNonZero(thresh2)
                if countNonZero > countNonZeroTarget:
                  low = thresValueToTry
                else:
                  high = thresValueToTry
            else:
              thresh2 = thresh

          thresh3 = thresh2.copy()

          if debugPlus:
            self._debugFrame(255 - thresh2, title="thresh2")

          if self._hyperparameters["headEmbeded"] and os.path.exists(os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName, f'{self._videoName}HP.csv')):
            headPositionFirstFrame = self._getHeadPositionByFileSaved()
          else:
            headPositionFirstFrame = 0
          if self._hyperparameters["headEmbeded"] and os.path.exists(os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName, f'{self._videoName}.csv')):
            tailTipFirstFrame = self._getTailTipByFileSaved()
          else:
            tailTipFirstFrame = 0
          if self._hyperparameters["headEmbeded"]:
            maxDepth = math.sqrt((headPositionFirstFrame[0] - tailTipFirstFrame[0])**2 + (headPositionFirstFrame[1] - tailTipFirstFrame[0])**2)
            maxDepth = 270 # Hack: need to change this
          else:
            maxDepth = 0

          lastFirstTheta = self._headTrackingHeadingCalculation(i, thresh2, thresh2, thresh2, thresh2, self._hyperparameters["erodeSize"], frame_width, frame_height, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection, headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"])

          if self._hyperparameters["trackTail"] == 1:
            for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
              self._tailTracking(animalId, i, 255 - thresh3 if self._hyperparameters["headEmbeded"] else thresh3, thresh3, thresh3, 0, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, maxDepth, tailTipFirstFrame, thresh3, 0, wellNumber)

          # Debug functions
          self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, curFrame)

        else:

          print("No predictions for frame", i, "and well number", wellNumber)

      print("done for frame", i)
      i = i + 1

    return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, 0, 0]

  def runTracking(self, wellNumber, background=None):
    if background is not None:
      self._background = background
    if self._background is None:
      self._background = self.getBackground()
    if self._hyperparameters["trackingDL"]:
      import torch
      return self._trackingDL(wellNumber, torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'), self._loadDLModel())

    if self._hyperparameters["fishTailTrackingDifficultBackground"]:
      [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals] = self._fishTailTrackingDifficultBackground(wellNumber)
      return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals, 0, 0]

    if (self._hyperparameters["freqAlgoPosFollow"] != 0):
      print("lastFrame:",self._lastFrame)

    thetaDiffAccept = 1.2 # 0.5 for the head embedded maybe
    maxDepth = 0

    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")

    heading = -1
    if self._hyperparameters["headEmbeded"]:
      heading = 0.7

    threshForBlackFrames = self._getThresForBlackFrame() # For headEmbededTeresaNicolson
    cap.set(1, self._firstFrame)

    # Using the first frame of the video to calculate parameters that will be used afterwards for the tracking
    if (self._hyperparameters["headEmbeded"] == 1):
      # Getting images

      if self._hyperparameters["headEmbededRemoveBack"] == 0 and self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0:
        [frame, thresh1] = self.headEmbededFrame(self._firstFrame, wellNumber)
      else:
        self._hyperparameters["headEmbededRemoveBack"] = 1
        self._hyperparameters["minPixelDiffForBackExtract"] = self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]
        [frame, thresh1] = self.headEmbededFrameBackExtract(self._background, self._firstFrame, wellNumber)

      # Setting self._hyperparameters in order to add line on image
      if self._hyperparameters["addBlackLineToImg_Width"]:
        self._addBlackLineToImgSetParameters(frame)

      # (x, y) coordinates for both eyes for head embedded fish eye tracking
      if self._hyperparameters["eyeTracking"] and self._hyperparameters["headEmbeded"] == 1:
        forEye = self.getAccentuateFrameForManualPointSelect(frame)
        if True:
          leftEyeCoordinate = list(self._getCoordinates(np.uint8(forEye * 255), "Click on the center of the left eye", True, True))
          rightEyeCoordinate = list(self._getCoordinates(np.uint8(forEye * 255), "Click on the center of the right eye", True, True))
        else:
          leftEyeCoordinate  = [261, 201] # [267, 198] # [210, 105]
          rightEyeCoordinate = [285, 157] # [290, 151] # [236, 72]
        print("leftEyeCoordinate:", leftEyeCoordinate)
        print("rightEyeCoordinate:", rightEyeCoordinate)

      # if self._hyperparameters["invertBlackWhiteOnImages"]:
        # frame   = 255 - frame

      gray = frame.copy()

      oppHeading = (heading + math.pi) % (2 * math.pi)

      # Getting headPositionFirstFrame and tailTipFirstFrame positions
      if os.path.exists(os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName, f'{self._videoName}HP.csv')):
        self._headPositionFirstFrame = self._getHeadPositionByFileSaved()
      else:
        if self._hyperparameters["findHeadPositionByUserInput"]:
          frameForManualPointSelection = self.getAccentuateFrameForManualPointSelect(frame)
          self._headPositionFirstFrame = self.findHeadPositionByUserInput(frameForManualPointSelection, self._firstFrame, wellNumber)
        else:
          [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = self._getImages(cap, self._firstFrame, wellNumber)
          cap.set(1, self._firstFrame)
          lastFirstTheta = self._headTrackingHeadingCalculation(self._firstFrame, blur, thresh1, thresh2, gray, self._hyperparameters["erodeSize"], int(cap.get(3)), int(cap.get(4)), self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection, self._headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"])
      if os.path.exists(os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName, f'{self._videoName}.csv')):
        self._tailTipFirstFrame  = self._getTailTipByFileSaved()
      else:
        frameForManualPointSelection = self.getAccentuateFrameForManualPointSelect(frame)
        self._tailTipFirstFrame  = self.findTailTipByUserInput(frameForManualPointSelection, self._firstFrame, wellNumber)
      if self._hyperparameters["automaticallySetSomeOfTheHeadEmbededHyperparameters"] == 1:
        self._adjustHeadEmbededHyperparameters(frame)
      # Getting max depth
      if self._hyperparameters["headEmbededTeresaNicolson"] == 1:
        if len(self._headPositionFirstFrame) == 0:
          self._headPositionFirstFrame = [self._trackingHeadTailAllAnimals[0][0][0][0], self._trackingHeadTailAllAnimals[0][0][0][1]]
        maxDepth = self._headEmbededTailTrackFindMaxDepthTeresaNicolson(frame)
      else:
        if self._hyperparameters["centerOfMassTailTracking"] == 0:
          if self._hyperparameters["headEmbededTailTrackingForImage"] == 0:
            maxDepth = self._headEmbededTailTrackFindMaxDepth(frame)
          else:
            maxDepth = self._headEmbededTailTrackFindMaxDepthForImage(frame)
        else:
          maxDepth = self._centerOfMassTailTrackFindMaxDepth(frame)

    widgets = None
    # Performing the tracking on each frame
    i = self._firstFrame
    if int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
      self._lastFrame = min(self._lastFrame, self._firstFrame + int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
    while (i < self._lastFrame+1):

      if (self._hyperparameters["freqAlgoPosFollow"] != 0) and (i % self._hyperparameters["freqAlgoPosFollow"] == 0):
        print("Tracking: wellNumber:",wellNumber," ; frame:",i)
        if self._hyperparameters["popUpAlgoFollow"]:
          from zebrazoom.code.popUpAlgoFollow import prepend
          prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
      if self._hyperparameters["debugTracking"]:
        print("frame:",i)
      # Get images for frame i
      [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = self._getImages(cap, i, wellNumber, 0, self._trackingHeadTailAllAnimals)
      # Head tracking and heading calculation
      lastFirstTheta = self._headTrackingHeadingCalculation(i, blur, thresh1, thresh2, gray, self._hyperparameters["erodeSize"], int(cap.get(3)), int(cap.get(4)), self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection, self._headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"], xHead, yHead)

      # Tail tracking for frame i
      if self._hyperparameters["trackTail"] == 1 :
        for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          self._tailTracking(animalId, i, frame, thresh1, threshForBlackFrames, thetaDiffAccept, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, lastFirstTheta, maxDepth, self._tailTipFirstFrame, initialCurFrame, back, wellNumber, xHead, yHead)

      if self._hyperparameters["updateBackgroundAtInterval"]:
        self._updateBackgroundAtInterval(i, wellNumber, initialCurFrame, self._trackingHeadTailAllAnimals, frame)

      # Eye tracking for frame i
      if self._hyperparameters["eyeTracking"]:
        if self._hyperparameters["headEmbeded"] == 1:
          if self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
            i, widgets = self._eyeTrackingHeadEmbedded(animalId, i, frame, thresh1, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets=widgets)
            if not self._hyperparameters["eyeFilterKernelSize"] % 2:
              self._hyperparameters["eyeFilterKernelSize"] -= 1
            continue
          else:
            self._eyeTrackingHeadEmbedded(animalId, i, frame, thresh1, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate)
        else:
          self._eyeTracking(animalId, i, frame, thresh1, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingEyesAllAnimals)

      # Debug functions
      if self._hyperparameters["nbAnimalsPerWell"] > 1 or self._hyperparameters["forceBlobMethodForHeadTracking"] or self._hyperparameters["headEmbeded"] == 1 or self._hyperparameters["fixedHeadPositionX"] != -1:
        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame)
      else:
        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame)
      # DetectMovementWithRawVideoInsideTracking
      if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
        self._detectMovementWithRawVideoInsideTracking(i, xHead, yHead, initialCurFrame)

      if self._hyperparameters["trackOnlyOnROI_halfDiameter"]:
        if not(xHead == 0 and yHead == 0):
          for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
            for j in range(0, len(self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame])): # Head Position should already shifted, only shifting tail positions now
              self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][0] = self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][0] + xHead
              self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][1] = self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][1] + yHead

      paramsAdjusted = self._adjustParameters(i, initialCurFrame, frame, frame2, back, widgets)
      if paramsAdjusted is not None:
        i, widgets = paramsAdjusted
      else:
        i = i + 1

    if self._hyperparameters["postProcessMultipleTrajectories"]:
      self._postProcessMultipleTrajectories(self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection)

    self._savingBlackFrames(self._trackingHeadTailAllAnimals)

    print("Tracking done for well", wellNumber)
    if self._hyperparameters["popUpAlgoFollow"]:
      from zebrazoom.code.popUpAlgoFollow import prepend
      prepend("Tracking done for well "+ str(wellNumber))

    if self._auDessusPerAnimalId is not None:
      return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals, self._headPositionFirstFrame, self._tailTipFirstFrame, self._auDessusPerAnimalId]
    else:
      return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals, self._headPositionFirstFrame, self._tailTipFirstFrame]

  def _getParametersForWell(self, wellNumber):
    '''Does the tracking and then the extraction of parameters'''
    if self.useGUI:
      from PyQt5.QtWidgets import QApplication

      if QApplication.instance() is None:
        from zebrazoom.GUIAllPy import PlainApplication
        app = PlainApplication(sys.argv)
    # Normal execution process
    parameters = extractParameters(self.runTracking(wellNumber), wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
    return wellNumber, parameters

  def _storeParametersInQueue(self, queue, wellNumber):
    queue.put(self._getParametersForWell(wellNumber))

  def run(self):
    self._background = self.getBackground()

    if self._hyperparameters["trackingDL"]:
      from torch.multiprocessing import Process
      import torch.multiprocessing as mp
    else:
      from multiprocessing import Process
      import multiprocessing as mp
    if globalVariables["mac"] or self._hyperparameters["trackingDL"]:
      mp.set_start_method('spawn', force=True)

    # Tracking and extraction of parameters
    if globalVariables["noMultiprocessing"] == 0 and not self._hyperparameters['headEmbeded']:
      if self._hyperparameters["onlyTrackThisOneWell"] == -1:
        # for all wells, in parallel
        queue = mp.Queue()
        processes = [Process(target=self._storeParametersInQueue, args=(queue, wellNumber), daemon=True)
                     for wellNumber in range(self._hyperparameters["nbWells"])]
        for p in processes:
          p.start()
        parametersPerWell = [queue.get() for p in processes]
        for p in processes:
          p.join()
      else:
        # for just one well
        parametersPerWell = [self._getParametersForWell(self._hyperparameters["onlyTrackThisOneWell"])]
    else:
      if self._hyperparameters["onlyTrackThisOneWell"] == -1:
        parametersPerWell = [self._getParametersForWell(wellNumber) for wellNumber in range(self._hyperparameters["nbWells"])]
      else:
        parametersPerWell = [self._getParametersForWell(self._hyperparameters["onlyTrackThisOneWell"])]

    # Sorting wells after the end of the parallelized calls end
    return {wellNumber: parameters for wellNumber, parameters in parametersPerWell}

register_tracking_method('tracking', Tracking)
