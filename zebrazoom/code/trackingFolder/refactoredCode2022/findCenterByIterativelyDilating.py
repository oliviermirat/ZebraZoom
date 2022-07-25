import cv2
import numpy as np

def findCenterByIterativelyDilating(initialContour, lenX, lenY):
  x = 0
  y = 0
  
  xmin = lenX
  ymin = lenY
  xmax = 0
  ymax = 0
  for pt in initialContour:
    if pt[0][0] < xmin:
      xmin = pt[0][0]
    if pt[0][1] < ymin:
      ymin = pt[0][1]
    if pt[0][0] > xmax:
      xmax = pt[0][0]
    if pt[0][1] > ymax:
      ymax = pt[0][1]
  
  for pt in initialContour:
    pt[0][0] = pt[0][0] - xmin
    pt[0][1] = pt[0][1] - ymin
  
  image = np.zeros((ymax - ymin, xmax - xmin))
  image[:, :] = 255
  image = image.astype(np.uint8)
  kernel  = np.ones((3, 3), np.uint8)
  if type(initialContour) != int:
    cv2.fillPoly(image, pts =[initialContour], color=(0))
    image[:,0] = 255
    image[0,:] = 255
    image[:, len(image[0])-1] = 255
    image[len(image)-1, :]    = 255
    nbBlackPixels = 1
    dilateIter = 0
    while nbBlackPixels > 0:
      dilateIter   = dilateIter + 1
      dilatedImage = cv2.dilate(image, kernel, iterations=dilateIter)
      nbBlackPixels = cv2.countNonZero(255-dilatedImage)
    dilateIter   = dilateIter - 1
    dilatedImage = cv2.dilate(image, kernel, iterations=dilateIter)
    dilatedImage[:,0] = 255
    dilatedImage[0,:] = 255
    dilatedImage[:, len(dilatedImage[0])-1] = 255
    dilatedImage[len(dilatedImage)-1, :]    = 255
    contours, hierarchy = cv2.findContours(dilatedImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    maxContour = 0
    maxContourArea = 0
    for contour in contours:
      contourArea = cv2.contourArea(contour)
      if contourArea < int((xmax - xmin) * (ymax - ymin) * 0.8):
        if contourArea > maxContourArea:
          maxContourArea = contourArea
          maxContour     = contour
    M = cv2.moments(maxContour)
    if M['m00']:
      x = int(M['m10']/M['m00'])
      y = int(M['m01']/M['m00'])
  
  return [x + xmin, y + ymin]
