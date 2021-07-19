from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.postProcessMultipleTrajectories import postProcessMultipleTrajectories
import multiprocessing as mp
from multiprocessing import Process
import cv2
import numpy as np

def fasterMultiprocessing(videoPath, background, wellPositions, output, hyperparameters, videoName):

  cap = cv2.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  nbTailPoints = hyperparameters["nbTailPoints"]
  
  trackingHeadTailAllAnimalsList = []
  trackingHeadingAllAnimalsList  = []
  trackingDataList               = []
  
  for wellNumber in range(0, hyperparameters["nbWells"]):
    trackingHeadTailAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2)))
    trackingHeadingAllAnimalsList.append(np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1)))
  
  i = firstFrame
  while (i < lastFrame + 1):
    
    if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % hyperparameters["freqAlgoPosFollow"] == 0):
      print("Tracking: frame:",i)
      if hyperparameters["popUpAlgoFollow"]:
        prepend("Tracking: frame:" + str(i))
    
    ret, frame = cap.read()
    
    for wellNumber in range(0,hyperparameters["nbWells"]):
      
      minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
      # if "minPixelDiffForBackExtractHead" in hyperparameters:
        # minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtractHead"]
      xtop = wellPositions[wellNumber]['topLeftX']
      ytop = wellPositions[wellNumber]['topLeftY']
      lenX = wellPositions[wellNumber]['lengthX']
      lenY = wellPositions[wellNumber]['lengthY']
      back = background[ytop:ytop+lenY, xtop:xtop+lenX]
      grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
      putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255
      blur = cv2.GaussianBlur(curFrame, (hyperparameters["paramGaussianBlur"], hyperparameters["paramGaussianBlur"]),0)
      
      [trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, 0, 0, 0, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], 0, wellPositions[wellNumber]["lengthX"])
    
    i = i + 1
    
  for wellNumber in range(0,hyperparameters["nbWells"]):
    [trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], trackingEyesAllAnimals] = postProcessMultipleTrajectories(trackingHeadingAllAnimalsList[wellNumber], trackingHeadTailAllAnimalsList[wellNumber], [], hyperparameters)  
    
    trackingDataList.append([trackingHeadTailAllAnimalsList[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0])
  
  for wellNumber in range(0,hyperparameters["nbWells"]):
    parameters = extractParameters(trackingDataList[wellNumber], wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.append([wellNumber,parameters,[]])
  
  return output