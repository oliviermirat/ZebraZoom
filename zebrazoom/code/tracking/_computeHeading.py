import math

import cv2
import numpy as np


class ComputeHeadingMixin:
  def _computeHeading(self, thresh1, x, y, headSize, wellNumber=-1, frameNumber=-1):
    if headSize == -1:
      # print("Setting headSize to 25 instead of -1, this may be a problem in some cases")
      headSize = 25 # This was introduced to fix bug when config file creation for center of mass only tracking 16/11/22

    videoWidth  = self._hyperparameters["videoWidth"]
    videoHeight = self._hyperparameters["videoHeight"]

    x = x + int(headSize)
    y = y + int(headSize)

    paddedImage = np.zeros((len(thresh1) + 2 * int(headSize), len(thresh1[0]) + 2 * int(headSize)))
    paddedImage[:, :] = 255
    paddedImage[int(headSize):len(thresh1)+int(headSize), int(headSize):len(thresh1[0])+int(headSize)] = thresh1
    thresh1 = paddedImage

    thresh1 = thresh1.astype(np.uint8)

    ymin  = y - headSize
    ymax  = y + headSize
    xmin  = x - headSize
    xmax  = x + headSize

    img = thresh1[int(ymin):int(ymax), int(xmin):int(xmax)]

    img[0,:] = 255
    img[len(img)-1,:] = 255
    img[:,0] = 255
    img[:,len(img[0])-1] = 255

    y, x = np.nonzero(img)
    x = x - np.mean(x)
    y = y - np.mean(y)
    coords = np.vstack([x, y])
    cov = np.cov(coords)
    evals, evecs = np.linalg.eig(cov)
    sort_indices = np.argsort(evals)[::-1]
    x_v1, y_v1 = evecs[:, sort_indices[0]]  # Eigenvector with largest eigenvalue
    x_v2, y_v2 = evecs[:, sort_indices[1]]
    scale = 20
    theta = self._calculateAngle(0, 0, x_v1, y_v1)
    theta = (theta - math.pi/2) % (2 * math.pi)
    
    if ("findHeadingOppDirectionThroughLineDrawing_radius" in self._hyperparameters) and (self._hyperparameters["findHeadingOppDirectionThroughLineDrawing_radius"]):
      imgOri = img.copy()
      imgInv = img.copy()
      radius = self._hyperparameters["findHeadingOppDirectionThroughLineDrawing_radius"]
      cv2.circle(imgOri, (headSize, headSize), radius, (255), -1)
      cv2.line(imgOri, (headSize, headSize), (int(headSize + headSize * math.cos(theta)), int(headSize + headSize * math.sin(theta))), (255), radius)
      cv2.circle(imgInv, (headSize, headSize), radius, (255), -1)
      cv2.line(imgInv, (headSize, headSize), (int(headSize - headSize * math.cos(theta)), int(headSize - headSize * math.sin(theta))), (255), radius)
      sumOri = cv2.countNonZero(imgOri)
      sumInv = cv2.countNonZero(imgInv)
      if wellNumber != -1 and frameNumber != -1:
        self._trackingProbabilityOfHeadingGoodCalculation[wellNumber][0, frameNumber-self._firstFrame] = sumInv - sumOri
      if sumInv < sumOri:
        theta = (theta + math.pi) % (2 * math.pi)
    
    if self._hyperparameters["debugHeadingCalculation"]:
      img2 = img.copy()
      img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
      cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img[0])/2 + 20 * math.cos(theta)), int(len(img)/2 + 20 * math.sin(theta))), (255,0,0), 1) #self._hyperparameters["findHeadingOppDirectionThroughLineDrawing_radius"] if "findHeadingOppDirectionThroughLineDrawing_radius" in self._hyperparameters else 1)
      self._debugFrame(img2, title='imgForHeadingCalculation')

    return theta

  def _calculateHeading(self, x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter, previousFrameHeading=0, wellNumber=-1):
    nbList = self._hyperparameters["nbList"]
    expDecreaseFactor = self._hyperparameters["expDecreaseFactor"]
    headSize = self._hyperparameters["headSize"]
    debugTracking = self._hyperparameters["debugTracking"]
    headEmbeded = self._hyperparameters["headEmbeded"]

    if self._hyperparameters["debugHeadingCalculation"]:
      self._debugFrame(thresh1, title='thresh1')
      self._debugFrame(thresh2, title='thresh2')

    cx = 0
    cy = 0
    cxNew = 0
    cyNew = 0

    thresh1[0,:]                 = 255
    thresh1[len(thresh1)-1,:]    = 255
    thresh1[:,0]                 = 255
    thresh1[:,len(thresh1[0])-1] = 255
    
    if not("findHeadingOppDirectionThroughLineDrawing_radius" in self._hyperparameters and self._hyperparameters["findHeadingOppDirectionThroughLineDrawing_radius"]):
      contours, hierarchy = cv2.findContours(thresh1,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (float(x), float(y)), True)
        if dist >= 0:
          M = cv2.moments(contour)
          if M['m00']:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            bodyContour = contour
          else:
            cx = 0
            cy = 0
          if self._hyperparameters["debugHeadingCalculation"]:
            print("dist, cx, cy:", dist, cx, cy)
            print("x, y:", x, y)

    if self._hyperparameters["debugHeadingCalculation"]:
      print("x, y, cx, cy:", x, y, cx, cy)

    heading = self._computeHeading(thresh2, x, y, headSize, wellNumber, i)
    
    if not("findHeadingOppDirectionThroughLineDrawing_radius" in self._hyperparameters and self._hyperparameters["findHeadingOppDirectionThroughLineDrawing_radius"]):
      
      if self._hyperparameters["debugHeadingCalculation"]:
        print("previousFrameHeading:", previousFrameHeading)
        print("math.sqrt((x - cx)**2 + (y - cy)**2):", math.sqrt((x - cx)**2 + (y - cy)**2))
      if math.sqrt((x - cx)**2 + (y - cy)**2) > 1:
        lastFirstTheta = self._calculateAngle(x, y, cx, cy)
      else:
        lastFirstTheta = (previousFrameHeading + math.pi) % (2 * math.pi)

      headingApproximate = lastFirstTheta
      headingPreciseOpt1 = heading
      headingPreciseOpt2 = (heading + math.pi) % (2*math.pi)
      diffAngle1 = self._distBetweenThetas(headingApproximate, headingPreciseOpt1)
      diffAngle2 = self._distBetweenThetas(headingApproximate, headingPreciseOpt2)
      if (diffAngle1 > diffAngle2):
        heading = headingPreciseOpt1
      else:
        heading = headingPreciseOpt2

      if self._hyperparameters["debugHeadingCalculation"]:
        print("headingApproximate:", headingApproximate)
        print("headingPreciseOpt1:", headingPreciseOpt1)
        print("headingPreciseOpt2:", headingPreciseOpt2)
        print("diffAngle1:", diffAngle1)
        print("diffAngle2:", diffAngle2)
        print("heading:", heading)
        
    else:
      
      lastFirstTheta = heading
    
    return [heading, lastFirstTheta]

  def _calculateHeadingSimple(self, x, y, thresh2):
    headSize = self._hyperparameters["headSize"]
    heading = self._computeHeading(thresh2, x, y, headSize)
    return heading
