import cv2
import math
import numpy as np

from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas

def computeHeading(thresh1, x, y, headSize, hyperparameters):
  
  videoWidth  = hyperparameters["videoWidth"]
  videoHeight = hyperparameters["videoHeight"]
  
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
  theta = calculateAngle(0, 0, x_v1, y_v1)
  theta = (theta - math.pi/2) % (2 * math.pi)
  
  if hyperparameters["debugHeadingCalculation"]:
    import zebrazoom.code.util as util

    img2 = img.copy()
    img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
    cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img[0])/2 + 20 * math.cos(theta)), int(len(img)/2 + 20 * math.sin(theta))), (255,0,0), 1)
    util.showFrame(img2, title='imgForHeadingCalculation')
  
  return theta


def calculateHeading(x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter, hyperparameters, previousFrameHeading=0):

  nbList = hyperparameters["nbList"]
  expDecreaseFactor = hyperparameters["expDecreaseFactor"]
  firstFrame = hyperparameters["firstFrame"]
  lastFrame = hyperparameters["lastFrame"]
  headSize = hyperparameters["headSize"]
  debugTracking = hyperparameters["debugTracking"]
  headEmbeded = hyperparameters["headEmbeded"]
  
  if hyperparameters["debugHeadingCalculation"]:
    import zebrazoom.code.util as util

    util.showFrame(thresh1, title='thresh1')
    util.showFrame(thresh2, title='thresh2')
  
  cx = 0
  cy = 0
  cxNew = 0
  cyNew = 0
    
  thresh1[0,:]                 = 255
  thresh1[len(thresh1)-1,:]    = 255
  thresh1[:,0]                 = 255
  thresh1[:,len(thresh1[0])-1] = 255
  
  contours, hierarchy = cv2.findContours(thresh1,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
  for contour in contours:
    dist = cv2.pointPolygonTest(contour, (x, y), True)
    if dist >= 0:
      M = cv2.moments(contour)
      if M['m00']:
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])
        bodyContour = contour
      else:
        cx = 0
        cy = 0
      if hyperparameters["debugHeadingCalculation"]:
        print("area:", area)
        print("dist, cx, cy:", dist, cx, cy)
        print("x, y:", x, y)
  
  if hyperparameters["debugHeadingCalculation"]:
    print("x, y, cx, cy:", x, y, cx, cy)
  
  heading = computeHeading(thresh2, x, y, headSize, hyperparameters)
  if hyperparameters["debugHeadingCalculation"]:
    print("previousFrameHeading:", previousFrameHeading)
    print("math.sqrt((x - cx)**2 + (y - cy)**2):", math.sqrt((x - cx)**2 + (y - cy)**2))
  if math.sqrt((x - cx)**2 + (y - cy)**2) > 1:
    lastFirstTheta = calculateAngle(x, y, cx, cy)
  else:
    lastFirstTheta = (previousFrameHeading + math.pi) % (2 * math.pi)
  
  headingApproximate = lastFirstTheta
  headingPreciseOpt1 = heading
  headingPreciseOpt2 = (heading + math.pi) % (2*math.pi)
  diffAngle1 = distBetweenThetas(headingApproximate, headingPreciseOpt1)
  diffAngle2 = distBetweenThetas(headingApproximate, headingPreciseOpt2)
  if (diffAngle1 > diffAngle2):
    heading = headingPreciseOpt1
  else:
    heading = headingPreciseOpt2
  
  if hyperparameters["debugHeadingCalculation"]:
    print("headingApproximate:", headingApproximate)
    print("headingPreciseOpt1:", headingPreciseOpt1)
    print("headingPreciseOpt2:", headingPreciseOpt2)
    print("diffAngle1:", diffAngle1)
    print("diffAngle2:", diffAngle2)
    print("heading:", heading)
  
  return [heading, lastFirstTheta]


def calculateHeadingSimple(x, y, thresh2, hyperparameters):
  
  headSize = hyperparameters["headSize"]
  heading = computeHeading(thresh2, x, y, headSize, hyperparameters)
  
  return heading
