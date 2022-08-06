import cv2

def detectMovementWithRawVideoInsideTracking2(hyperparameters, trackingHeadTailAllAnimalsList, previousFrames, animal_Id, i, firstFrame, auDessusPerAnimalIdList, grey, wellPositions):
  halfDiameterRoiBoutDetect = hyperparameters["halfDiameterRoiBoutDetect"]
  if previousFrames.full():
    previousFrame   = previousFrames.get()
    curFrame        = grey.copy()
    for wellNumber in range(0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"], hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
      # previousXYCoord = previousXYCoords.get()
      headX = trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-firstFrame][0][0]
      headY = trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-firstFrame][0][1]
      xmin = headX - hyperparameters["halfDiameterRoiBoutDetect"]
      ymin = headY - hyperparameters["halfDiameterRoiBoutDetect"]
      xmax = xmin + 2 * hyperparameters["halfDiameterRoiBoutDetect"]
      ymax = ymin + 2 * hyperparameters["halfDiameterRoiBoutDetect"]
      lenX = wellPositions[wellNumber]['lengthX']
      lenY = wellPositions[wellNumber]['lengthY']
      if xmin < 0:
        xmin = 0
      if ymin < 0:
        ymin = 0
      if xmax > lenX - 1:
        xmax = lenX - 1
      if ymax > lenY - 1:
        ymax = lenY - 1
      if ymax < ymin:
        ymax = ymin + 2 * hyperparameters["halfDiameterRoiBoutDetect"]
      if xmax < xmin:
        xmax = xmin + 2 * hyperparameters["halfDiameterRoiBoutDetect"]
      if ( (xmin > lenX - 1) or (xmax < 0) ):
        xmin = 0
        xmax = 0 + lenX - 1
      if ( (ymin > lenY - 1) or (ymax < 0) ):
        ymin = 0
        ymax = 0 + lenY - 1
      xmin = int(xmin + wellPositions[wellNumber]['topLeftX'])
      xmax = int(xmax + wellPositions[wellNumber]['topLeftX'])
      ymin = int(ymin + wellPositions[wellNumber]['topLeftY'])
      ymax = int(ymax + wellPositions[wellNumber]['topLeftY'])
      # img22       = img2[ymin:ymax, xmin:xmax]
      # imgFuture22 = imgFuture2[ymin:ymax, xmin:xmax]
      # maxX = min(len(previousFrame[0]), len(curFrame[0]))
      # maxY = min(len(previousFrame), len(curFrame))
      # print("Av: aaa:", len(previousFrame))
      # print("Av: bbb:", len(previousFrame[0]))
      # print("1Av: aaa:", len(grey))
      # print("1Av: bbb:", len(grey[0]))
      subPreviousFrame = previousFrame[ymin:ymax, xmin:xmax].copy()
      subCurFrame      = curFrame[ymin:ymax, xmin:xmax].copy()
      # print("Aft: aaa:", len(previousFrame))
      # print("Aft: bbb:", len(previousFrame[0]))            
      # if i > 250 and wellNumber == 3:
        # import zebrazoom.code.util as util
        # print("wellNumber:", wellNumber, "; headX, headY:", headX, headY, "; xmin, xmax, ymin, ymax:", xmin, xmax, ymin, ymax)
        # print("aaa:", len(previousFrame))
        # print("bbb:", len(previousFrame[0]))
        # util.showFrame(subPreviousFrame, title='subPreviousFrame' + str(wellNumber))
        # util.showFrame(subCurFrame,      title='subCurFrame' + str(wellNumber))
      
      # Possible optimization in the future: refine the ROI based on halfDiameterRoiBoutDetect !!!
      res = cv2.absdiff(subPreviousFrame, subCurFrame)
      ret, res = cv2.threshold(res,hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)
      totDiff = cv2.countNonZero(res)
      
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        if totDiff > hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
          auDessusPerAnimalIdList[wellNumber][animalId][i-firstFrame] = 1
        else:
          auDessusPerAnimalIdList[wellNumber][animalId][i-firstFrame] = 0
  else:
    for wellNumber in range(0 if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"], hyperparameters["nbWells"] if hyperparameters["onlyTrackThisOneWell"] == -1 else hyperparameters["onlyTrackThisOneWell"] + 1):
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        auDessusPerAnimalIdList[wellNumber][animalId][i-firstFrame] = 0
  previousFrames.put(grey)
  # previousXYCoords.put([xHead, yHead])
  
  return [auDessusPerAnimalIdList, previousFrames]
