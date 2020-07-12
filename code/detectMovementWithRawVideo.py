import numpy as np
import cv2
from getImageSequential import getImageSequential
from getImage import getImage
from adjustHyperparameters import initializeAdjustHyperparametersWindows, adjustHyperparameters, getDetectMouvRawVideosParamsForHyperParamAdjusts

def getImagesAndTotDiff(head, rayon, cap1, cap2, videoPath, l, frameGapComparision, wellNumber, wellPositions, hyperparameters, firstFrame, lenX, lenY, thresForDetectMovementWithRawVideo):
  headX = head[l-firstFrame][0]
  headY = head[l-firstFrame][1]
  xmin = headX - rayon
  ymin = headY - rayon
  xmax = xmin + 2 * rayon
  ymax = ymin + 2 * rayon
  if xmin < 0:
    xmin = 0
  if ymin < 0:
    ymin = 0
  if xmax > lenX - 1:
    xmax = lenX - 1
  if ymax > lenY - 1:
    ymax = lenY - 1
  
  if ymax < ymin:
    ymax = ymin + 2 * rayon

  if xmax < xmin:
    xmax = xmin + 2 * rayon
  
  if ( (xmin > lenX - 1) or (xmax < 0) ):
    xmin = 0
    xmax = 0 + lenX - 1

  if ( (ymin > lenY - 1) or (ymax < 0) ):
    ymin = 0
    ymax = 0 + lenY - 1

  if hyperparameters["adjustDetectMovWithRawVideo"]:
    img = getImage(videoPath, l, wellNumber, wellPositions, hyperparameters)
    imgFuture = getImage(videoPath, l+frameGapComparision, wellNumber, wellPositions, hyperparameters)  
  else:
    img = getImageSequential(cap1, videoPath, l, wellNumber, wellPositions, hyperparameters)
    imgFuture = getImageSequential(cap2, videoPath, l+frameGapComparision, wellNumber, wellPositions, hyperparameters)
  
  img2 = img.copy()
  imgFuture2 = imgFuture.copy()
  
  res = img.copy()
  
  # cvSetImageROI(img2, cvRect(xmin,ymin,xmax-xmin,ymax-ymin))
  # cvSetImageROI(imgFuture2, cvRect(xmin,ymin,xmax-xmin,ymax-ymin))
  # cvSetImageROI(res, cvRect(xmin,ymin,xmax-xmin,ymax-ymin))
  
  # img2[ymin:ymax, xmin:xmax]
  # imgFuture2[ymin:ymax, xmin:xmax]
  # res[ymin:ymax, xmin:xmax]
  
  # cvAbsDiff(img2,imgFuture2,res)
  
  xmin = int(xmin)
  xmax = int(xmax)
  ymin = int(ymin)
  ymax = int(ymax)
  
  img22       = img2[ymin:ymax, xmin:xmax]
  imgFuture22 = imgFuture2[ymin:ymax, xmin:xmax]
  
  blackCircleHalfDiam = hyperparameters["addBlackCircleOfHalfDiamOnHeadForBoutDetect"]
  if blackCircleHalfDiam:
    cv2.circle(img22, (int(headX), int(headY)), int(blackCircleHalfDiam), (0, 0, 0), -1)
    cv2.circle(imgFuture22, (int(headX), int(headY)), int(blackCircleHalfDiam), (0, 0, 0), -1)
    # cv2.imshow("img22", img22)
    # cv2.waitKey(0)
  
  res = cv2.absdiff(img22, imgFuture22)
  
  ret, res = cv2.threshold(res,thresForDetectMovementWithRawVideo,255,cv2.THRESH_BINARY)
  
  totDiff = cv2.countNonZero(res)
  
  return [img[ymin:ymax, xmin:xmax], res, totDiff, cap1, cap2]

  
def detectMovementWithRawVideo(hyperparameters, videoPath, background, wellNumber, wellPositions, head):
  
  if hyperparameters["adjustDetectMovWithRawVideo"]:
    initializeAdjustHyperparametersWindows("Bouts Detection")
  organizationTabCur = []
  
  if hyperparameters["debugDetectMovWithRawVideo"]:
    print("detectMovementWithRawVideo")
    cv2.namedWindow("debugDetectMovWithRawVideo")
    cv2.moveWindow("debugDetectMovWithRawVideo", 0, 0)
  
  if hyperparameters["wellsAreRectangles"]:
    lenX = int(wellPositions[wellNumber]["lengthX"])
    lenY = int(wellPositions[wellNumber]["lengthY"])
  else:
    lenX = hyperparameters["wellOutputVideoDiameter"]
    lenY = hyperparameters["wellOutputVideoDiameter"]
  
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  
  l       = firstFrame
  debut_l = firstFrame
  max_l   = lastFrame
  
  mouvement = [0] * (max_l-debut_l+1)
  
  cap1 = cv2.VideoCapture(videoPath)
  cap1.set(1, debut_l)
  
  cap2 = cv2.VideoCapture(videoPath)
  cap2.set(1, debut_l + hyperparameters["frameGapComparision"])
  
  while ((l < max_l) and (l-firstFrame < len(head))) or hyperparameters["adjustDetectMovWithRawVideo"]:
    if l >= debut_l:
      
      if l < hyperparameters["firstFrame"]:
        l = hyperparameters["firstFrame"]
  
      if l > hyperparameters["lastFrame"]:
        l = hyperparameters["lastFrame"]
      
      [img, res, totDiff, cap1, cap2] = getImagesAndTotDiff(head, hyperparameters["halfDiameterRoiBoutDetect"], cap1, cap2, videoPath, l, hyperparameters["frameGapComparision"], wellNumber, wellPositions, hyperparameters, firstFrame, lenX, lenY, hyperparameters["thresForDetectMovementWithRawVideo"])
      
      if hyperparameters["debugDetectMovWithRawVideo"]:
        print("frame:",l," ; number of different pixel in subsequent frames:",totDiff," ; bout detection threshold:",hyperparameters["minNbPixelForDetectMovementWithRawVideo"])
        if hyperparameters["debugDetectMovWithRawVideoShowVid"]:
          cv2.imshow("debugDetectMovWithRawVideo", res)
          cv2.waitKey(0)
      
      if totDiff > hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
        mouvement[l-firstFrame] = 1
      else:
        mouvement[l-firstFrame] = 0
      
      if hyperparameters["adjustDetectMovWithRawVideo"]:
        
        [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab] = getDetectMouvRawVideosParamsForHyperParamAdjusts(img, res, l, totDiff, hyperparameters)
        if len(organizationTabCur) == 0:
          organizationTabCur = organizationTab
      
        [l, hyperparameters, organizationTabCur] = adjustHyperparameters(l, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTabCur)
      else:
        l = l + 1
      
    else:
      l = l + 1
  
  return mouvement
