import numpy as np
import cv2

def medianAndMinimum(img, hyperparameters):
  medianImage = cv2.medianBlur(img, hyperparameters["imagePreProcessParameters"][0])
  img = np.minimum(img, medianImage)
  return img

def preprocessImage(img, hyperparameters):
  
  if hyperparameters["imagePreProcessMethod"] == "medianAndMinimum":
    img = medianAndMinimum(img, hyperparameters)
  
  return img
