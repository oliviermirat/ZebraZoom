from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util

def headEmbededFrameBackExtract(videoPath, background, hyperparameters, frameNumber):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  debug = 0
  
  cap = zzVideoReading.VideoCapture(videoPath)
  
  cap.set(1, frameNumber)
  ret, frame = cap.read()
  
  while not(ret):
    print("WARNING: couldn't read the frameNumber", frameNumber, "for the video", hyperparameters["videoName"])
    frameNumber = frameNumber - 1
    cap.set(1, frameNumber)
    ret, frame = cap.read()
  
  if ("invertBlackWhiteOnImages" in hyperparameters) and hyperparameters["invertBlackWhiteOnImages"]:
    frame = 255 - frame
    
  if ("imagePreProcessMethod" in hyperparameters) and hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
  
  kernel = np.ones((8,8),np.float32)/25
  thres1  = cv2.filter2D(frame,-1,kernel)
  retval, thres1 = cv2.threshold(thres1, 80, 255, cv2.THRESH_BINARY)
  
  frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  thres1 = cv2.cvtColor(thres1, cv2.COLOR_BGR2GRAY)

  if (debug):
    util.showFrame(frame, title='thres1')
  
  putToWhite = ( frame.astype('int32') >= (background.astype('int32') + minPixelDiffForBackExtract) )
  # This puts the pixels that belong to a fish to white
  frame[putToWhite] = 255
  
  if (debug):
    util.showFrame(frame, title='thres1')
    # cv2.imshow('thres1', thres1)
    # cv2.waitKey(0)
    
  thres1 = 255 - thres1
  frame  = 255 - frame
  
  return [frame, thres1]
