import numpy as np
import cv2

def medianAndMinimum(img, hyperparameters):

  medianImage = cv2.medianBlur(img, hyperparameters["imagePreProcessParameters"][0])
  img = np.minimum(img, medianImage)
  
  return img
  
def erodeThenDilate(img, hyperparameters):

  kernelErodeSize = hyperparameters["imagePreProcessParameters"][0]
  kernelErode = np.ones((kernelErodeSize, kernelErodeSize), np.uint8)
  img = cv2.erode(img, kernelErode)
  
  kernelDilateSize = hyperparameters["imagePreProcessParameters"][1]
  kernelDilate = np.ones((kernelDilateSize, kernelDilateSize), np.uint8)
  img = cv2.dilate(img, kernelDilate)
  
  return img

def preprocessImage(img, hyperparameters):
  
  if hyperparameters["imagePreProcessMethod"] == "medianAndMinimum":    
    img = medianAndMinimum(img, hyperparameters)
  elif hyperparameters["imagePreProcessMethod"] == "erodeThenDilate":
    img = erodeThenDilate(img, hyperparameters)
  
  return img
