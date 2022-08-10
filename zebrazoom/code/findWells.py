import h5py
import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.preprocessImage import preprocessImage
import math
import json
import sys
import os
from scipy import interpolate
from zebrazoom.code.adjustHyperparameters import adjustHyperparameters


def _findRectangularWellsAreaQt(frame, videoPath, hyperparameters):
  import zebrazoom.code.util as util

  topLeft, bottomRight = util.getRectangle(frame, "Click on the top left and bottom right of one of the wells")
  return abs(topLeft[0] - bottomRight[0]) * abs(topLeft[1] - bottomRight[1])


def findRectangularWellsArea(frame, videoPath, hyperparameters):
  from PyQt5.QtWidgets import QApplication

  return _findRectangularWellsAreaQt(frame, videoPath, hyperparameters, dialog=not hasattr(QApplication.instance(), 'window'))


def findRectangularWells(frame, videoPath, hyperparameters, rectangularWellsArea, widgets=None):
  
  findRectangleWellArea                    = rectangularWellsArea
  hyperparameters["findRectangleWellArea"] = rectangularWellsArea
  
  rectangleWellAreaImageThreshold    = hyperparameters["rectangleWellAreaImageThreshold"]
  rectangleWellErodeDilateKernelSize = hyperparameters["rectangleWellErodeDilateKernelSize"]
  rectangularWellsInvertBlackWhite   = hyperparameters["rectangularWellsInvertBlackWhite"]
  
  rectangularWellStretchPercentage     = hyperparameters["rectangularWellStretchPercentage"]
  rectangleWellAreaTolerancePercentage = hyperparameters["rectangleWellAreaTolerancePercentage"]
  nbPixelToleranceRectangleArea    = int(findRectangleWellArea * (rectangleWellAreaTolerancePercentage / 100))
  minRectangleArea                 = findRectangleWellArea - nbPixelToleranceRectangleArea
  maxRectangleArea                 = findRectangleWellArea + nbPixelToleranceRectangleArea
  
  wellPositions = []
  
  gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  
  if rectangularWellsInvertBlackWhite:
    gray  = 255 - gray

  retval, gray = cv2.threshold(gray, rectangleWellAreaImageThreshold, 255, cv2.THRESH_BINARY)

  kernel = np.ones((rectangleWellErodeDilateKernelSize, rectangleWellErodeDilateKernelSize), np.uint8)
  if rectangularWellsInvertBlackWhite:
    gray = cv2.dilate(gray, kernel, iterations = 1)
    gray = cv2.erode(gray,  kernel, iterations = 1)  
  else:
    gray = cv2.erode(gray,  kernel, iterations = 1)
    gray = cv2.dilate(gray, kernel, iterations = 1)

  contours, hierarchy = cv2.findContours(gray, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
  for contour in contours:
    print("Possible Well Area:", cv2.contourArea(contour))
    if cv2.contourArea(contour) > minRectangleArea and cv2.contourArea(contour) < maxRectangleArea:
      if not(hyperparameters["rectangularWellMinMaxXandYmethod"]):
        topLeftCoord          = [0, 0]
        bottomRightCoord      = [0, 0]
        topLeftDistToZero     = float("inf")
        bottomRightDistToZero = -1
        for point in contour:
          if math.sqrt(point[0][0]**2 + point[0][1]**2) < topLeftDistToZero:
            topLeftDistToZero = math.sqrt(point[0][0]**2 + point[0][1]**2)
            topLeftCoord = point[0]
          if math.sqrt(point[0][0]**2 + point[0][1]**2) > bottomRightDistToZero:
            bottomRightDistToZero = math.sqrt(point[0][0]**2 + point[0][1]**2)
            bottomRightCoord = point[0]
        stretchDist = int(math.sqrt((bottomRightCoord[0] - topLeftCoord[0] if bottomRightCoord[0] - topLeftCoord[0] >= 0 else 0) * (bottomRightCoord[1] - topLeftCoord[1] if bottomRightCoord[1] - topLeftCoord[1] >= 0 else 0)) * (rectangularWellStretchPercentage / 100))
        well = {'topLeftX': int(topLeftCoord[0] - stretchDist), 'topLeftY': int(topLeftCoord[1] - stretchDist), 'lengthX': int(bottomRightCoord[0] - topLeftCoord[0] + 2 * stretchDist), 'lengthY': int(bottomRightCoord[1] - topLeftCoord[1] + 2 * stretchDist)}
      else:
        top    = float("inf")
        bottom = -1
        left   = float("inf")
        right  = -1
        for point in contour:
          if point[0][1] < top:
            top    = point[0][1]
          if point[0][1] > bottom:
            bottom = point[0][1]
          if point[0][0] < left:
            left   = point[0][0]
          if point[0][0] > right:
            right  = point[0][0]
        well = {'topLeftX' : int(left-hyperparameters["rectangularWellMinMaxXandYmethodMargin"]), 'topLeftY' : int(top-hyperparameters["rectangularWellMinMaxXandYmethodMargin"]), 'lengthX' : int(right - left + 2*hyperparameters["rectangularWellMinMaxXandYmethodMargin"]), 'lengthY': int(bottom - top + 2*hyperparameters["rectangularWellMinMaxXandYmethodMargin"])}
      
      wellPositions.append(well)
  
  if hyperparameters["adjustRectangularWellsDetect"]:
    
    gray   = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    frame2 = frame.copy()
    rectangleTickness = 2
    lengthY = len(frame)
    lengthX = len(frame[0])
    if len(wellPositions):
      perm1 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
      perm2 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
      perm3 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
      for i in range(0, len(wellPositions)):
        if hyperparameters["wellsAreRectangles"]:
          topLeft     = (wellPositions[i]['topLeftX'], wellPositions[i]['topLeftY'])
          bottomRight = (wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'], wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'])
          color = (int(perm1[i]), int(perm2[i]), int(perm3[i]))
          frame2 = cv2.rectangle(frame2, topLeft, bottomRight, color, rectangleTickness)
    
    hyperparametersListNames = ["rectangleWellAreaImageThreshold", "rectangleWellErodeDilateKernelSize","findRectangleWellArea", "rectangularWellsInvertBlackWhite"]
    organizationTab = [
    [0, 255, "Adjust this threshold in order to get the inside of the wells as white as possible and the well's borders as black as possible."],
    [0, 75, "Increase the value of this parameter if some sections of the well's borders are not black (if there are some 'holes' in the borders)."],
    [0, 50000, "Only change the value of this parameter as a last resort (and change it 'slowly' if you do). This parameter represents the mean area of the wells to detect."],
    [0, 1, "Put this value to 1 if and only if the inside of your wells are darker than the well's borders in your video."],]
    WINDOW_NAME = "Rectangular Wells Detection: Adjust parameters until you get the right number of wells detected (on the right side)"
    frameToShow = np.concatenate((gray, frame2), axis=1)
    
    cv2.putText(frameToShow, "Wells detected:" + str(len(wellPositions)), (int(len(frameToShow[0])/2), 80), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 0, 255), 8)
  
    l, widgets = adjustHyperparameters(None, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab, widgets)
    
    for param in hyperparametersListNames:
      hyperparameters[param] = int(hyperparameters[param])
    if hyperparameters["rectangularWellsInvertBlackWhite"] > 1:
      hyperparameters["rectangularWellsInvertBlackWhite"] = 1
    
    findRectangularWells(frame, videoPath, hyperparameters, hyperparameters["findRectangleWellArea"], widgets=widgets)
  
  return wellPositions


def findCircularWells(frame, videoPath, hyperparameters):

  minWellDistanceForWellDetection = hyperparameters["minWellDistanceForWellDetection"]
  wellOutputVideoDiameter         = hyperparameters["wellOutputVideoDiameter"]

  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

  circles2 = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, minWellDistanceForWellDetection)
  if hyperparameters["debugFindWells"] and (hyperparameters["exitAfterBackgroundExtraction"] == 0):
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel, QVBoxLayout

    import zebrazoom.code.util as util
    label = QLabel()
    label.setMinimumSize(1, 1)
    layout = QVBoxLayout()
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    util.showDialog(layout, title='Frame', labelInfo=(gray, label))
  
  circles = np.uint16(np.around(circles2))

  wellPositions = []

  for circle in circles[0,:]:
    xtop = int(circle[0] - (wellOutputVideoDiameter/2))
    ytop = int(circle[1] - (wellOutputVideoDiameter/2))
    if xtop < 0:
      xtop = 0
    if ytop < 0:
      ytop = 0
    nx   = wellOutputVideoDiameter
    ny   = wellOutputVideoDiameter
    well = { 'topLeftX' : xtop , 'topLeftY' : ytop , 'lengthX' : nx , 'lengthY': ny }
    wellPositions.append(well)
  
  return wellPositions


def saveWellsRepartitionImage(wellPositions, frame, hyperparameters):
  rectangleTickness = 2
  lengthY = len(frame)
  lengthX = len(frame[0])
  if len(wellPositions):
    perm1 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
    perm2 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
    perm3 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
    for i in range(0, len(wellPositions)):
      if hyperparameters["wellsAreRectangles"] or len(hyperparameters["oneWellManuallyChosenTopLeft"]) or int(hyperparameters["multipleROIsDefinedDuringExecution"]) or hyperparameters["noWellDetection"] or hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]:
        topLeft     = (wellPositions[i]['topLeftX'], wellPositions[i]['topLeftY'])
        bottomRight = (wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'], wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'])
        color = (int(perm1[i]), int(perm2[i]), int(perm3[i]))
        frame = cv2.rectangle(frame, topLeft, bottomRight, color, rectangleTickness)
      else:
        cv2.circle(frame, (int(wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'] / 2), int(wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'] / 2)), 170, (0,0,255), 2)
      cv2.putText(frame, str(i), (int(wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'] / 2), int(wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'] / 2)), cv2.FONT_HERSHEY_SIMPLEX, 1,(255,255,255),2,cv2.LINE_AA)
  frame = cv2.resize(frame, (int(lengthX/2), int(lengthY/2))) # ???
  cv2.imwrite(os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), "repartition.jpg"), frame )
  return frame


def _groupOfMultipleSameSizeAndShapeEquallySpacedWellsQt(videoPath, hyperparameters):
  from PyQt5.QtCore import Qt, QTimer
  from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout

  import zebrazoom.code.util as util

  cap = zzVideoReading.VideoCapture(videoPath)
  if (cap.isOpened()== False):
    print("Error opening video stream or file")
  ret, frame = cap.read()
  nonRotatedFrame = frame.copy()
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)

  accepted = False
  while not accepted:
    positions = ("top left", "top right", "bottom left")
    idx = 0
    posCoord = {}
    app = QApplication.instance()
    if getattr(app, 'configFileHistory', None):
      def back():
        nonlocal idx
        idx -= 1
    else:
      back = None
    while idx < len(positions):
      oldidx = idx
      if not idx and not hyperparameters["exitAfterBackgroundExtraction"] and back is None:

        def rotateVideo(video):
          nonlocal frame
          if hyperparameters["backgroundPreProcessMethod"] == ["rotate"] and hyperparameters["imagePreProcessMethod"] == ["rotate"] and \
              hyperparameters["imagePreProcessParameters"][0][0] == hyperparameters["backgroundPreProcessParameters"][0][0]:
            angle = hyperparameters["imagePreProcessParameters"][0][0]
          else:
            angle = 0.

          angle = util.getRotationAngle(nonRotatedFrame, angle, dialog=not hasattr(app, 'window'))
          if angle is None:
            return
          value = float("{:.2f}".format(angle))
          rotationAngleParams = {"backgroundPreProcessMethod": ["rotate"],
                                 "imagePreProcessMethod": ["rotate"],
                                 "backgroundPreProcessParameters": [[value]],
                                 "imagePreProcessParameters": [[value]]}
          hyperparameters.update(rotationAngleParams)
          outputFolderVideo = os.path.join(hyperparameters["outputFolder"], os.path.splitext(os.path.basename(videoPath))[0])
          import pickle
          with open(os.path.join(outputFolderVideo, 'rotationAngle.txt'), 'wb') as outfile:
            pickle.dump(rotationAngleParams, outfile)
          with open(os.path.join(outputFolderVideo, 'configUsed.json'), 'r') as f:
            config = json.load(f)
          config.update(rotationAngleParams)
          with open(os.path.join(outputFolderVideo, 'configUsed.json'), 'w') as f:
            json.dump(config, f)
          frame = cv2.warpAffine(nonRotatedFrame, cv2.getRotationMatrix2D(tuple(x / 2 for x in frame.shape[1::-1]), value, 1.0), frame.shape[1::-1], flags=cv2.INTER_LINEAR)
          util.setPixmapFromCv(frame, video)
        extraBtns = (('Rotate video', rotateVideo, False),)
      else:
        extraBtns = ()
      posCoord[positions[idx]] = np.array(list(util.getPoint(frame, "Click on the " + positions[idx] + " of the group of wells", extraButtons=extraBtns,
                                                             selectingRegion=True, backBtnCb=back, useNext=False, dialog=not hasattr(app, 'window'))))
      if idx != oldidx:
        if idx >= 0:
          continue
        QTimer.singleShot(0, app.configFileHistory[-2])
        return None
      idx += 1

    nbWellsPerRows = hyperparameters["nbWellsPerRows"]
    nbRowsOfWells  = hyperparameters["nbRowsOfWells"]

    l = []

    vectorX = (posCoord["top right"] - posCoord["top left"]) / nbWellsPerRows
    vectorY = (posCoord["bottom left"] - posCoord["top left"]) / nbRowsOfWells

    for row in range(0, nbRowsOfWells):
      for col in range(0, nbWellsPerRows):

        wellTopLeft     = posCoord["top left"] + col * vectorX + row * vectorY
        wellTopRight    = wellTopLeft + vectorX
        wellBottomLeft  = wellTopLeft + vectorY
        wellBottomRight = wellTopLeft + vectorX + vectorY

        minX = min([wellTopLeft[0], wellTopRight[0], wellBottomLeft[0], wellBottomRight[0]])
        minY = min([wellTopLeft[1], wellTopRight[1], wellBottomLeft[1], wellBottomRight[1]])
        maxX = max([wellTopLeft[0], wellTopRight[0], wellBottomLeft[0], wellBottomRight[0]])
        maxY = max([wellTopLeft[1], wellTopRight[1], wellBottomLeft[1], wellBottomRight[1]])

        well = {'topLeftX' : int(minX), 'topLeftY' : int(minY), 'lengthX' : int(maxX - minX), 'lengthY': int(maxY - minY)}
        l.append(well)

    possibleRepartition = saveWellsRepartitionImage(l, frame.copy(), hyperparameters)

    label = QLabel()
    label.setMinimumSize(1, 1)
    layout = QVBoxLayout()
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

    def accept():
      nonlocal accepted
      accepted = True
    buttons = (("Yes, this is a good repartition.", accept), ("No, I want to try again.", None))
    if hasattr(app, 'window'):
      util.showBlockingPage(layout, title="Is this a good repartition of wells?", buttons=buttons, labelInfo=(possibleRepartition, label))
    else:
      util.showDialog(layout, title="Is this a good repartition of wells?", buttons=buttons, labelInfo=(possibleRepartition, label))

  cap.release()
  return l


def _multipleROIsDefinedDuringExecutionQt(videoPath, hyperparameters):
  import zebrazoom.code.util as util

  l = [None] * hyperparameters["nbWells"]
  frames = l[:]
  cap = zzVideoReading.VideoCapture(videoPath)
  if (cap.isOpened()== False):
    print("Error opening video stream or file")
  ret, frame = cap.read()
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
  frameForRepartitionJPG = frame.copy()
  i = 0
  app = QApplication.instance()
  if getattr(app, 'configFileHistory', None):
    def back():
      nonlocal i
      i -= 1
  else:
    back = None
  while i < hyperparameters["nbWells"]:
    oldi = i
    if frames[i] is not None:
      frame = frames[i].copy()
    else:
      frames[i] = frame.copy()
    topLeft, bottomRight = util.getRectangle(frame, "Select one of the regions of interest", backBtnCb=back, dialog=not hasattr(app, 'window'))
    if oldi != i:
      if i >= 0:
        frames[oldi] = None
        continue
      QTimer.singleShot(0, app.configFileHistory[-2])
      return None
    frame = cv2.rectangle(frame, (topLeft[0], topLeft[1]), (bottomRight[0], bottomRight[1]), (255, 0, 0), 1)
    frame_width  = bottomRight[0] - topLeft[0]
    frame_height = bottomRight[1] - topLeft[1]
    well = {'topLeftX' : topLeft[0], 'topLeftY' : topLeft[1], 'lengthX' : frame_width, 'lengthY': frame_height}
    l[i] = well
    i += 1
  saveWellsRepartitionImage(l, frameForRepartitionJPG, hyperparameters)
  cap.release()
  return l


def findWells(videoPath, hyperparameters):

  if hyperparameters["noWellDetection"]:
    
    cap = zzVideoReading.VideoCapture(videoPath)
    if (cap.isOpened()== False): 
      print("Error opening video stream or file")
    ret, frame = cap.read()
    if hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, hyperparameters)
    frame_width  = int(cap.get(3))
    frame_height = int(cap.get(4))
    l = []
    well = { 'topLeftX' : 0 , 'topLeftY' : 0 , 'lengthX' : frame_width , 'lengthY': frame_height }
    l.append(well)
    saveWellsRepartitionImage(l, frame, hyperparameters)
    cap.release()
    return l
  
  # Group of multiple same size and shape equally spaced wells
  
  if int(hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]):
    return _groupOfMultipleSameSizeAndShapeEquallySpacedWellsQt(videoPath, hyperparameters)
  
  # Multiple ROIs defined by user during the execution
  
  if int(hyperparameters["multipleROIsDefinedDuringExecution"]):
    return _multipleROIsDefinedDuringExecutionQt(videoPath, hyperparameters)
  
  # One ROI definied in the configuration file
  
  if len(hyperparameters["oneWellManuallyChosenTopLeft"]):
    l = []
    topLeft_X = hyperparameters["oneWellManuallyChosenTopLeft"][0]
    topLeft_Y = hyperparameters["oneWellManuallyChosenTopLeft"][1]
    bottomRight_X = hyperparameters["oneWellManuallyChosenBottomRight"][0]
    bottomRight_Y = hyperparameters["oneWellManuallyChosenBottomRight"][1]
    frame_width  = bottomRight_X - topLeft_X
    frame_height = bottomRight_Y - topLeft_Y
    well = { 'topLeftX' : topLeft_X , 'topLeftY' : topLeft_Y , 'lengthX' : frame_width , 'lengthY': frame_height }
    l.append(well)
    cap = zzVideoReading.VideoCapture(videoPath)
    if (cap.isOpened()== False): 
      print("Error opening video stream or file")
    ret, frame = cap.read()
    if hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, hyperparameters)
    saveWellsRepartitionImage(l, frame, hyperparameters)
    cap.release()
    return l
  
  # Circular or rectangular wells
  
  cap = zzVideoReading.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  ret, frame = cap.read()
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
  if hyperparameters["invertBlackWhiteOnImages"]:
    frame = 255 - frame
  
  if hyperparameters["wellsAreRectangles"]:
    if hyperparameters["adjustRectangularWellsDetect"]:
      rectangularWellsArea = findRectangularWellsArea(frame, videoPath, hyperparameters)
    else:
      rectangularWellsArea = hyperparameters["findRectangleWellArea"]
      
    wellPositions = findRectangularWells(frame, videoPath, hyperparameters, rectangularWellsArea)
  else:
    wellPositions = findCircularWells(frame, videoPath, hyperparameters)
  
  cap.release()
  
  # Sorting wells
  
  nbWellsPerRows = hyperparameters["nbWellsPerRows"]
  nbRowsOfWells  = hyperparameters["nbRowsOfWells"]
  
  if len(wellPositions) >= nbWellsPerRows * nbRowsOfWells:
    
    for i in range(0, len(wellPositions)):
      for j in range(0, len(wellPositions)-1):
        if wellPositions[j]['topLeftY'] > wellPositions[j+1]['topLeftY']:
          aux                = wellPositions[j]
          wellPositions[j]   = wellPositions[j+1]
          wellPositions[j+1] = aux
    
    if (nbRowsOfWells == 0):
      for i in range(0, len(wellPositions)):
        for j in range(0, len(wellPositions)-1):
          if wellPositions[j]['topLeftX'] > wellPositions[j+1]['topLeftX']:
            aux                = wellPositions[j]
            wellPositions[j]   = wellPositions[j+1]
            wellPositions[j+1] = aux
    else:
      for k in range(0, nbRowsOfWells):
        for i in range(nbWellsPerRows*k, nbWellsPerRows*(k+1)):
          for j in range(nbWellsPerRows*k, nbWellsPerRows*(k+1)-1):
            if wellPositions[j]['topLeftX'] > wellPositions[j+1]['topLeftX']:
              aux                = wellPositions[j]
              wellPositions[j]   = wellPositions[j+1]
              wellPositions[j+1] = aux   
  
  else:
    
    print("Not enough wells detected, please adjust your configuration file")
  
  lengthY = len(frame)
  lengthX = len(frame[0])
  
  if len(wellPositions):
    for i in range(0, len(wellPositions)):
      topLeftX = wellPositions[i]['topLeftX']
      wellPos_lengthX = wellPositions[i]['lengthX']
      topLeftY = wellPositions[i]['topLeftY']
      wellPos_lengthY = wellPositions[i]['lengthY']
      if topLeftX < 0:
        wellPositions[i]['topLeftX'] = 0
      if topLeftY < 0:
        wellPositions[i]['topLeftY'] = 0
      if topLeftX + wellPos_lengthX >= lengthX:
        wellPositions[i]['lengthX'] = lengthX - topLeftX - 1
      if topLeftY + wellPos_lengthY >= lengthY:
        wellPositions[i]['lengthY'] = lengthY - topLeftY - 1
  
  saveWellsRepartitionImage(wellPositions, frame, hyperparameters)
  
  if hyperparameters["debugFindWells"]:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel, QVBoxLayout

    import zebrazoom.code.util as util

    label = QLabel()
    label.setMinimumSize(1, 1)
    layout = QVBoxLayout()
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    timeout = 3000 if hyperparameters["exitAfterBackgroundExtraction"] else None
    util.showDialog(layout, title='Wells Detection', labelInfo=(frame, label), timeout=timeout)
  
  print("Wells found")
  
  if hyperparameters["popUpAlgoFollow"]:
    import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

    popUpAlgoFollow.prepend("Wells found")

  return wellPositions
