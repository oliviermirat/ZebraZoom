import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
from zebrazoom.code.getImage.getImageSequential import getImageSequential
from zebrazoom.code.getImage.getImage import getImage
from zebrazoom.code.adjustHyperparameters import adjustDetectMouvRawVideosParams

def putTabIntoBoundaries(img, tab):
  if tab[0] < 0:
    tab[0] = 0
  if tab[1] < 0:
    tab[1] = 0
  if tab[0] > len(img[0]) - 1:
    tab[0] = len(img[0]) - 1
  if tab[1] > len(img) - 1:
    tab[1] = len(img) - 1
  return tab

def getImagesAndTotDiff(head, rayon, cap1, cap2, videoPath, l, frameGapComparision, wellNumber, wellPositions, hyperparameters, firstFrame, lenX, lenY, thresForDetectMovementWithRawVideo, headPosition, tailTip):
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
    img       = cap1[l - firstFrame]
    if l + frameGapComparision - firstFrame < len(cap1):
      imgFuture = cap1[int(l + frameGapComparision - firstFrame)]
    else:
      imgFuture = cap1[len(cap1) - 1]
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
  if not(hyperparameters["noPreProcessingOfImageForBoutDetection"]) and blackCircleHalfDiam:
    cv2.circle(img22, (int(headX), int(headY)), int(blackCircleHalfDiam), (0, 0, 0), -1)
    cv2.circle(imgFuture22, (int(headX), int(headY)), int(blackCircleHalfDiam), (0, 0, 0), -1)
    # cv2.imshow("img22", img22)
    # cv2.waitKey(0)
  
  res = cv2.absdiff(img22, imgFuture22)
  
  if not(hyperparameters["noPreProcessingOfImageForBoutDetection"]) and type(headPosition) != int and type(tailTip) != int and len(headPosition) and len(tailTip):
    # Setting to black everything outside of a rectangle centered on the tail
    stencil = np.zeros(res.shape).astype(res.dtype)
    dist = (math.sqrt((headPosition[0] - tailTip[0])**2 + (headPosition[1] - tailTip[1])**2))*1.2
    center      = [(headPosition[0] + tailTip[0])/2, (headPosition[1] + tailTip[1])/2]
    topLeft     = [int(center[0] - dist/2) , int(center[1] - dist/2)]
    bottomRight = [int(center[0] + dist/2) , int(center[1] + dist/2)]
    topLeft     = putTabIntoBoundaries(res, topLeft)
    bottomRight = putTabIntoBoundaries(res, bottomRight)
    contours = [np.array([topLeft, [topLeft[0], bottomRight[1]], bottomRight, [bottomRight[0], topLeft[1]]])]
    color = [255, 255, 255]
    cv2.fillPoly(stencil, contours, color)
    res = cv2.bitwise_and(res, stencil)
    # Setting to black a polygon around the head of the animal
    pol1 = np.array(headPosition) + np.array([headPosition[1] - tailTip[1], tailTip[0] - headPosition[0]])
    pol2 = np.array(headPosition) + np.array([tailTip[1] - headPosition[1], headPosition[0] - tailTip[0]])
    pol3 = pol1 + np.array(headPosition) - np.array(tailTip)
    pol4 = pol2 + np.array(headPosition) - np.array(tailTip)
    pol1 = putTabIntoBoundaries(res, pol1.tolist())
    pol2 = putTabIntoBoundaries(res, pol2.tolist())
    pol3 = putTabIntoBoundaries(res, pol3.tolist())
    pol4 = putTabIntoBoundaries(res, pol4.tolist())
    pts = np.array([pol1,pol2,pol4,pol3], np.int32)
    cv2.fillPoly(res, [pts], (0,0,0))
  
  ret, res = cv2.threshold(res,thresForDetectMovementWithRawVideo,255,cv2.THRESH_BINARY)
  
  totDiff = cv2.countNonZero(res)
  
  return [img[ymin:ymax, xmin:xmax], res, totDiff, cap1, cap2]

  
def detectMovementWithRawVideo(hyperparameters, videoPath, background, wellNumber, wellPositions, head, headPositionFirstFrame, tailTipFirstFrame):
  
  if hyperparameters["adjustDetectMovWithRawVideo"]:
    widgets = None
  
  if hyperparameters["debugDetectMovWithRawVideo"]:
    print("detectMovementWithRawVideo")
  
  # if hyperparameters["wellsAreRectangles"]:
  lenX = int(wellPositions[wellNumber]["lengthX"])
  lenY = int(wellPositions[wellNumber]["lengthY"])
  # else:
    # lenX = hyperparameters["wellOutputVideoDiameter"]
    # lenY = hyperparameters["wellOutputVideoDiameter"]
  
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  
  l       = firstFrame
  debut_l = firstFrame
  max_l   = lastFrame
  
  mouvement = [0] * (max_l-debut_l+1)
  
  if hyperparameters["adjustDetectMovWithRawVideo"]:
    cap1 = []
    cap2 = 0
    cap = zzVideoReading.VideoCapture(videoPath)
    cap.set(1, debut_l)
    for k in range(debut_l, max_l):
      imgTemp = getImageSequential(cap, videoPath, k, wellNumber, wellPositions, hyperparameters)
      cap1.append(imgTemp)
  else:
    cap1 = zzVideoReading.VideoCapture(videoPath)
    cap1.set(1, debut_l)
    cap2 = zzVideoReading.VideoCapture(videoPath)
    cap2.set(1, debut_l + hyperparameters["frameGapComparision"])
  
  while ((l < max_l) and (l-firstFrame < len(head))) or hyperparameters["adjustDetectMovWithRawVideo"]:
    if l >= debut_l:
      
      if l < hyperparameters["firstFrame"]:
        l = hyperparameters["firstFrame"]
  
      if l > hyperparameters["lastFrame"]:
        l = hyperparameters["lastFrame"]
      
      [img, res, totDiff, cap1, cap2] = getImagesAndTotDiff(head, hyperparameters["halfDiameterRoiBoutDetect"], cap1, cap2, videoPath, l, hyperparameters["frameGapComparision"], wellNumber, wellPositions, hyperparameters, firstFrame, lenX, lenY, hyperparameters["thresForDetectMovementWithRawVideo"], headPositionFirstFrame, tailTipFirstFrame)
      
      if hyperparameters["debugDetectMovWithRawVideo"]:
        print("frame:",l," ; number of different pixel in subsequent frames:",totDiff," ; bout detection threshold:",hyperparameters["minNbPixelForDetectMovementWithRawVideo"])
        if hyperparameters["debugDetectMovWithRawVideoShowVid"]:
          import zebrazoom.code.util as util
          util.showFrame(res, title="debugDetectMovWithRawVideo")
      
      if totDiff > hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
        mouvement[l-firstFrame] = 1
      else:
        mouvement[l-firstFrame] = 0
      
      if hyperparameters["adjustDetectMovWithRawVideo"]:
      
        if l + hyperparameters["frameGapComparision"] > hyperparameters["lastFrame"]:
          l = int(hyperparameters["lastFrame"] - hyperparameters["frameGapComparision"] - 3)
        l, widgets = adjustDetectMouvRawVideosParams(img, res, l, totDiff, hyperparameters, widgets)
        if l + hyperparameters["frameGapComparision"] > hyperparameters["lastFrame"]:
          l = int(hyperparameters["lastFrame"] - hyperparameters["frameGapComparision"] - 3)
          
      else:
        l = l + 1
      
    else:
      l = l + 1
  
  return mouvement
