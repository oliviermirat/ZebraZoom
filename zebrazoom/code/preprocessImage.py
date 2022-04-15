import numpy as np
import cv2

def findNonGrayScalePixels(image, hyperparameters):
  
  if len(hyperparameters["oneWellManuallyChosenTopLeft"]):
    xtop = hyperparameters["oneWellManuallyChosenTopLeft"][0]
    ytop = hyperparameters["oneWellManuallyChosenTopLeft"][1]
    lenX = hyperparameters["oneWellManuallyChosenBottomRight"][0] - xtop
    lenY = hyperparameters["oneWellManuallyChosenBottomRight"][1] - ytop
  else:
    xtop = 0
    ytop = 0
    lenX = len(image[0])
    lenY = len(image)
  
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  gray2 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

  image = image.astype(np.int32)
  gray2 = gray2.astype(np.int32)

  fin = abs(image - gray2)
  fin = fin.astype(np.uint8)

  fin2 = cv2.cvtColor(fin, cv2.COLOR_BGR2GRAY)
  fin2 = 255 - fin2
  
  thresh = 245
  ret, fin3 = cv2.threshold(fin2, thresh, 255, cv2.THRESH_BINARY)
  numberOfBlackPixels =  lenX * lenY - np.sum(fin3[ytop:ytop+lenY, xtop:xtop+lenX])/255
  
  previousThres = []
  while (numberOfBlackPixels < 50 or numberOfBlackPixels > 80) and thresh < 254 and not(thresh in previousThres):
    previousThres.append(thresh)
    if numberOfBlackPixels < 50:
      # if not(thresh + 1 in previousThres):
      thresh = thresh + 1
    else:
      # if not(thresh - 1 in previousThres):
      thresh = thresh - 1
    ret, fin3 = cv2.threshold(fin2, thresh, 255, cv2.THRESH_BINARY)
    numberOfBlackPixels =  lenX * lenY - np.sum(fin3[ytop:ytop+lenY, xtop:xtop+lenX])/255
    # print("AAA: thresh:", thresh, "; numberOfBlackPixels:", numberOfBlackPixels)
    
  # print("thresh used:", thresh, "; numberOfBlackPixels:", numberOfBlackPixels)
  
  kernel = np.ones((6, 6), np.uint8)
  fin3 = cv2.erode(fin3, kernel, iterations = 1)
  
  fin3 = cv2.cvtColor(fin3, cv2.COLOR_GRAY2BGR)

  return fin3


def medianBlur(img, hyperparameters, imagePreProcessParameters):
  
  img = cv2.medianBlur(img, imagePreProcessParameters[0])
  
  return img


def medianAndMinimum(img, hyperparameters, imagePreProcessParameters):
  
  medianImage = cv2.medianBlur(img, imagePreProcessParameters[0])
  img = np.minimum(img, medianImage)
  
  return img


def erodeThenDilate(img, hyperparameters, imagePreProcessParameters):

  kernelErodeSize = imagePreProcessParameters[0]
  kernelErode = np.ones((kernelErodeSize, kernelErodeSize), np.uint8)
  img = cv2.erode(img, kernelErode)
  
  kernelDilateSize = imagePreProcessParameters[1]
  kernelDilate = np.ones((kernelDilateSize, kernelDilateSize), np.uint8)
  img = cv2.dilate(img, kernelDilate)
  
  return img

def erodeThenMin(img, hyperparameters, imagePreProcessParameters):
  
  kernel  = np.ones((3, 3), np.uint8)
  img2 = cv2.erode(img, kernel, iterations=imagePreProcessParameters[0])
  img3 = cv2.min(img, img2)
  
  return img3
  
def setImageLineToBlack(img, hyperparameters, imagePreProcessParameters):
  
  img = cv2.line(img, (imagePreProcessParameters[0], imagePreProcessParameters[1]), (imagePreProcessParameters[2], imagePreProcessParameters[3]), (0, 0, 0), imagePreProcessParameters[4])
  
  return img

def rotateImage(img, hyperparameters, imagePreProcessParameters):
  
  image_center = tuple(np.array(img.shape[1::-1]) / 2)
  rot_mat = cv2.getRotationMatrix2D(image_center, imagePreProcessParameters[0], 1.0)
  img = cv2.warpAffine(img, rot_mat, img.shape[1::-1], flags=cv2.INTER_LINEAR)
  
  return img


def preprocessImage(img, hyperparameters):
  
  if type(hyperparameters["imagePreProcessMethod"]) == list:
    imagePreProcessMethodList     = hyperparameters["imagePreProcessMethod"].copy()
    imagePreProcessParametersList = hyperparameters["imagePreProcessParameters"].copy()
  else:
    imagePreProcessMethodList     = [hyperparameters["imagePreProcessMethod"]]
    imagePreProcessParametersList = [hyperparameters["imagePreProcessParameters"]]
  
  while len(imagePreProcessMethodList):
    imagePreProcessMethod     = imagePreProcessMethodList.pop(0)
    imagePreProcessParameters = imagePreProcessParametersList.pop(0)
    if imagePreProcessMethod == "medianAndMinimum":
      img = medianAndMinimum(img, hyperparameters, imagePreProcessParameters)
    if imagePreProcessMethod == "medianBlur":
      img = medianBlur(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "erodeThenDilate":
      img = erodeThenDilate(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "findNonGrayScalePixels":
      img = findNonGrayScalePixels(img, hyperparameters)
    elif imagePreProcessMethod == "erodeThenMin":
      img = erodeThenMin(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "setImageLineToBlack":
      img = setImageLineToBlack(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "rotate":
      img = rotateImage(img, hyperparameters, imagePreProcessParameters)
    
  return img


def preprocessBackgroundImage(img, hyperparameters):
  
  if type(hyperparameters["backgroundPreProcessMethod"]) == list:
    imagePreProcessMethodList     = hyperparameters["backgroundPreProcessMethod"].copy()
    imagePreProcessParametersList = hyperparameters["backgroundPreProcessParameters"].copy()
  else:
    imagePreProcessMethodList     = [hyperparameters["backgroundPreProcessMethod"]]
    imagePreProcessParametersList = [hyperparameters["backgroundPreProcessParameters"]]
  
  while len(imagePreProcessMethodList):
    imagePreProcessMethod     = imagePreProcessMethodList.pop(0)
    imagePreProcessParameters = imagePreProcessParametersList.pop(0)
    if imagePreProcessMethod == "medianAndMinimum":
      img = medianAndMinimum(img, hyperparameters, imagePreProcessParameters)
    if imagePreProcessMethod == "medianBlur":
      img = medianBlur(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "erodeThenDilate":
      img = erodeThenDilate(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "findNonGrayScalePixels":
      img = findNonGrayScalePixels(img, hyperparameters)
    elif imagePreProcessMethod == "erodeThenMin":
      img = erodeThenMin(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "setImageLineToBlack":
      img = setImageLineToBlack(img, hyperparameters, imagePreProcessParameters)
    elif imagePreProcessMethod == "rotate":
      img = rotateImage(img, hyperparameters, imagePreProcessParameters)
  
  return img
