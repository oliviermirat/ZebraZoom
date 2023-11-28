import numpy as np
import cv2

def getNewFrameROI(self, k, frame, wellNumber, animalId):

  # Retrieving ROI coordinates and selecting ROI
  roiXStart = self._wellPositions[wellNumber]['topLeftX'] + int(self._trackingDataPerWell[wellNumber][animalId][k][0][0] - self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"])
  roiYStart = self._wellPositions[wellNumber]['topLeftY'] + int(self._trackingDataPerWell[wellNumber][animalId][k][0][1] - self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"])
  roiXEnd   = roiXStart + 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
  roiYEnd   = roiYStart + 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
  if roiXStart < 0:
    roiXStart = 0
    roiXEnd   = 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
  if roiYStart < 0:
    roiYStart = 0
    roiYEnd   = 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
  if roiXEnd >= len(frame[0]):
    roiXEnd   = len(frame[0]) - 1
    roiXStart = len(frame[0]) - 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
  if roiYEnd >= len(frame):
    roiYEnd   = len(frame) - 1
    roiYStart = len(frame) - 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
  frameROI = frame[roiYStart:roiYEnd, roiXStart:roiXEnd].copy()
  
  # Subtracting background of image
  backgroundROI = self._background[roiYStart:roiYEnd, roiXStart:roiXEnd]
  frameROI = 255 - np.where(backgroundROI >= frameROI, backgroundROI - frameROI, 0).astype(np.uint8)

  # Applying gaussian filter
  paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
  frameROI = cv2.GaussianBlur(frameROI, (paramGaussianBlur, paramGaussianBlur), 0)
  
  return frameROI