import numpy as np
import cv2
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow
from zebrazoom.code.preprocessImage import preprocessImage

def getBackground(videoPath, hyperparameters):

  cap   = cv2.VideoCapture(videoPath)
  max_l = int(cap.get(7))

  backCalculationStep = hyperparameters["backCalculationStep"]
  if "firstFrame" in hyperparameters:
    firstFrame = hyperparameters["firstFrame"]
  else:
    firstFrame = 1
  if "lastFrame" in hyperparameters:
    lastFrame  = hyperparameters["lastFrame"]
  else:
    lastFrame  = max_l - 10
  debugExtractBack    = hyperparameters["debugExtractBack"]
  
  if backCalculationStep == -1:
    backCalculationStep = int((lastFrame - firstFrame) / hyperparameters["nbImagesForBackgroundCalculation"])
    if backCalculationStep <= 1:
      backCalculationStep = 1
  
  ret, back = cap.read()
  back = cv2.cvtColor(back, cv2.COLOR_BGR2GRAY)
  for k in range(firstFrame,lastFrame):
    if (k % backCalculationStep == 0):
      cap.set(1, k)
      ret, frame = cap.read()
      if debugExtractBack:
        print(k)
      if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if hyperparameters["extractBackWhiteBackground"]:
          back = cv2.max(frame, back)
        else:
          back = cv2.min(frame, back)
      else:
        print("couldn't use the frame", k, "for the background extraction")
  
  if hyperparameters["imagePreProcessMethod"]:
    back = preprocessImage(back, hyperparameters)
  
  if (debugExtractBack):
      
    cv2.imshow('Background extracted', back)
    if hyperparameters["exitAfterBackgroundExtraction"]:
      cv2.waitKey(3000)
    else:
      cv2.waitKey(0)
    cv2.destroyAllWindows()
    
  cap.release()
  
  print("Background Extracted")
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Background Extracted")
  
  return back
