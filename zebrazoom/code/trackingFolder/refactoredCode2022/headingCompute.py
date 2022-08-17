import zebrazoom.code.util as util
import numpy as np
import math
import cv2

def computeHeading2(initialContour, lenX, lenY, headPosition, hyperparameters):
  
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
  
  headPosition = [headPosition[0] - xmin, headPosition[1] - ymin]
  
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
  
  originalShape = 255 - image
  
  # Heading calculation: first approximation
  minWhitePixel = 1000000000
  bestAngle     = 0
  nTries        = 50
  for i in range(0, nTries):
    angleOption = i * ((2 * math.pi) / nTries)
    startPoint = (int(headPosition[0]), int(headPosition[1]))
    endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
    testImage  = originalShape.copy()
    testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
    nbWhitePixels = cv2.countNonZero(testImage)
    
    if nbWhitePixels < minWhitePixel:
      minWhitePixel = nbWhitePixels
      bestAngle     = angleOption
  bestAngleAfterFirstStep = bestAngle
  
  # Heading calculation: second (and refined) approximation
  # Searching for the optimal value of iterationsForErodeImageForHeadingCalculation
  countTries = 0
  nbIterations2nbWhitePixels = {}
  if "iterationsForErodeImageForHeadingCalculation" in hyperparameters:
    iterationsForErodeImageForHeadingCalculation = hyperparameters["iterationsForErodeImageForHeadingCalculation"]
  else:
    iterationsForErodeImageForHeadingCalculation = 4
  kernel = np.ones((3, 3), np.uint8)
  nbWhitePixelsMax = 0.3 * cv2.contourArea(initialContour)
  while (iterationsForErodeImageForHeadingCalculation > 0) and (countTries < 50) and not(iterationsForErodeImageForHeadingCalculation in nbIterations2nbWhitePixels):
    testImage2 = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
    nbWhitePixels = cv2.countNonZero(testImage2)
    nbIterations2nbWhitePixels[iterationsForErodeImageForHeadingCalculation] = nbWhitePixels
    if nbWhitePixels < nbWhitePixelsMax:
      iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation - 1
    if nbWhitePixels >= nbWhitePixelsMax:
      iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation + 1
    countTries = countTries + 1
  best_iterations = 0
  minDist = 10000000000000
  for iterations in nbIterations2nbWhitePixels:
    nbWhitePixels = nbIterations2nbWhitePixels[iterations]
    dist = abs(nbWhitePixels - nbWhitePixelsMax)
    if dist < minDist:
      minDist = dist
      best_iterations = iterations
  iterationsForErodeImageForHeadingCalculation = best_iterations
  hyperparameters["iterationsForErodeImageForHeadingCalculation"] = iterationsForErodeImageForHeadingCalculation
  
  testImage2 = cv2.erode(originalShape.copy(), kernel, iterations = iterationsForErodeImageForHeadingCalculation)
  
  maxDist = -1
  for i in range(0, nTries):
    angleOption = bestAngleAfterFirstStep - (math.pi / 5) + i * ((2 * (math.pi / 5)) / nTries)
    
    startPoint = (int(headPosition[0]), int(headPosition[1]))
    endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
    
    testImage = testImage2.copy()
    
    testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
    nbWhitePixels = cv2.countNonZero(testImage)
    if nbWhitePixels < minWhitePixel:
      minWhitePixel = nbWhitePixels
      bestAngle     = angleOption
    
  theta = bestAngle
  
  if hyperparameters["debugHeadingCalculation"]:
    img2 = image.copy()
    img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2RGB)
    cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img2[0])/2 + 20 * math.cos(theta)), int(len(img2)/2 + 20 * math.sin(theta))), (255,0,255), 1)
    util.showFrame(img2, title='imgForHeadingCalculation')
  
  return theta + math.pi
  
# def computeHeading(thresh1, x, y, hyperparameters):
  
  # videoWidth  = hyperparameters["videoWidth"]
  # videoHeight = hyperparameters["videoHeight"]
  # headSize = hyperparameters["headSize"]
  # ymin  = y - headSize - 10 if y - headSize >= 0 else 0
  # ymax  = y + headSize + 10 if y + headSize < len(thresh1) else len(thresh1) - 1
  # xmin  = x - headSize - 10 if x - headSize >= 0 else 0
  # xmax  = x + headSize + 10 if x + headSize < len(thresh1[0]) else len(thresh1[0]) - 1
  # img = thresh1[int(ymin):int(ymax), int(xmin):int(xmax)]
  
  # img[0,:] = 255
  # img[len(img)-1,:] = 255
  # img[:,0] = 255
  # img[:,len(img[0])-1] = 255
  
  # y2, x2 = np.nonzero(img)
  # x2 = x2 - np.mean(x2)
  # y2 = y2 - np.mean(y2)
  # coords = np.vstack([x2, y2])
  # cov = np.cov(coords)
  # evals, evecs = np.linalg.eig(cov)
  # sort_indices = np.argsort(evals)[::-1]
  # x_v1, y_v1 = evecs[:, sort_indices[0]]  # Eigenvector with largest eigenvalue
  # x_v2, y_v2 = evecs[:, sort_indices[1]]
  # scale = 20
  # theta = calculateAngle(0, 0, x_v1, y_v1)
  # theta = (theta - math.pi/2) % (2 * math.pi)
  
  # if False:
    # width  = len(img[0])
    # height = len(img)
    # option1X = x + width * math.cos(theta)
    # option1Y = y + height * math.sin(theta)
    # option2X = x - width * math.cos(theta)
    # option2Y = y - height * math.sin(theta)
    # if math.sqrt((option1X - width)**2 + (option1Y - height)**2) < math.sqrt((option2X - width)**2 + (option2Y - height)**2):
      # theta += theta + math.pi
  
  # if hyperparameters["debugHeadingCalculation"]:
    # img2 = img.copy()
    # img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
    # cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img[0])/2 + 20 * math.cos(theta)), int(len(img)/2 + 20 * math.sin(theta))), (255,0,0), 1)
    # util.showFrame(img2, title='imgForHeadingCalculation')
  
  # return theta