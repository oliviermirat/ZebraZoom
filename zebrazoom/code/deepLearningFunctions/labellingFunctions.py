from pathlib import Path
import os
import json
import numpy as np
import math
import cv2


def drawWhitePointsOnInitialImages(initialCurFrame, back, hyperparameters):
  import zebrazoom.code.util as util

  img = util.drawPoints(initialCurFrame.copy(), "Draw white points and click on any key when you're done")
  putToWhite = ( img.astype('int32') >= (back.astype('int32') - hyperparameters["minPixelDiffForBackExtract"]) )
  img[putToWhite] = 255      
  ret, thresh1 = cv2.threshold(img, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
  erodeSize = hyperparameters["erodeSize"]
  kernel    = np.ones((erodeSize,erodeSize), np.uint8)
  thresh1   = cv2.erode(thresh1, kernel, iterations=hyperparameters["erodeIter"])
  
  return [img, thresh1]


def saveImagesAndData(hyperparameters, bodyContour, initialCurFrame, wellNumber, frameNumber):
  
  if hyperparameters["saveBodyMaskResampleContourNbPoints"]:
    bodyContour2  = bodyContour.copy()
    contourLength = 0
    for contourInd in range(len(bodyContour) - 2):
      pt1 = bodyContour[contourInd][0]
      pt2 = bodyContour[contourInd+1][0]
      contourLength = contourLength + math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
    step = contourLength / hyperparameters["saveBodyMaskResampleContourNbPoints"]
    curLength = 0
    curPoint  = 0
    indexToDelete = []
    for contourInd in range(len(bodyContour) - 2):
      pt1 = bodyContour[contourInd][0]
      pt2 = bodyContour[contourInd+1][0]
      curLength = curLength + math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
      if curLength >= curPoint * step:
        curPoint = curPoint + 1
      else:
        indexToDelete.append(contourInd)
    indexToDelete.reverse()
    
    for indToDelete in indexToDelete:
      bodyContour2 = np.delete(bodyContour2, indToDelete, 0)
    bodyContour = bodyContour2
  
  if type(bodyContour) != int and len(bodyContour) and type(initialCurFrame) != int:
    initialCurFrame2 = initialCurFrame.copy()
    initialCurFrame2 = cv2.cvtColor(initialCurFrame2, cv2.COLOR_GRAY2RGB)
    lenX = len(initialCurFrame2[0])
    lenY = len(initialCurFrame2)
    for contourPt in bodyContour:
      pt1 = contourPt[0]
      initialCurFrame2 = cv2.circle(initialCurFrame2, (pt1[0], pt1[1]), 1, (255, 0, 0), -1)
    
    if hyperparameters["bodyMask_saveDataForAllFrames"]:
      answerYes = True        
    else:
      import zebrazoom.code.util as util

      answerYes = False

      def saveClicked():
        nonlocal answerYes
        answerYes = True
      buttons = (("Save", saveClicked), ("Discard", None))
      util.showFrame(initialCurFrame2, title="Is this a good delimitation of the body of the animal?", buttons=buttons)
    
    if answerYes:
      
      if hyperparameters["bodyMask_saveAsPngMask"]:
        originalShape = np.zeros((lenY, lenX))
        originalShape[:, :] = 0
        originalShape = originalShape.astype(np.uint8)
        cv2.fillPoly(originalShape, pts =[bodyContour], color=(1))
      
      pathToImg = os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"])
      imgName   = hyperparameters["videoName"] + '_well' + str(wellNumber) + '_frame' + str(frameNumber)
      
      if not(os.path.exists(pathToImg)):
        os.mkdir(pathToImg)
      if not(os.path.exists(os.path.join(pathToImg, 'PNGMasks'))):
        os.mkdir(os.path.join(pathToImg, 'PNGMasks'))
      if not(os.path.exists(os.path.join(pathToImg, 'PNGImages'))):
        os.mkdir(os.path.join(pathToImg, 'PNGImages'))
      
      cv2.imwrite(os.path.join(os.path.join(pathToImg, 'PNGImages'), imgName + '.png'), initialCurFrame)
      if hyperparameters["bodyMask_saveAsPngMask"]:
        cv2.imwrite(os.path.join(os.path.join(pathToImg, 'PNGMasks'),  imgName + '_mask.png'), originalShape)
      
      if hyperparameters["bodyMask_saveAsLabelMeJsonFormat"]:
        # Labels can then be reloaded and changed with the command: labelme --nodata
        
        jsonData = '''
            {
              "version": "4.5.9",
              "flags": {},
              "shapes": [
                {
                  "label": "Person",
                  "group_id": null,
                  "shape_type": "polygon",
                  "flags": {}
                }],
              "imageData": null
            }
            '''
        jsonData = json.loads(jsonData)
        jsonData['shapes'][0]['points'] = [elem[0].tolist() for elem in bodyContour]
        jsonData['imagePath']   = imgName + ".png"
        jsonData['imageHeight'] = lenY
        jsonData['imageWidth']  = lenX
        
        with open(os.path.join(os.path.join(pathToImg, 'PNGImages'), imgName + '.json'), 'w') as outfile:
          json.dump(jsonData, outfile)


def createMask(pathToImgFolder):
  
  pathToMaskDir = Path(pathToImgFolder)
  pathToMaskDir = pathToMaskDir.parent
  pathToMaskDir = os.path.join(pathToMaskDir, 'PNGMasks')
  if not(os.path.exists(pathToMaskDir)):
    os.mkdir(pathToMaskDir)
  
  os.walk(pathToImgFolder)
  for x in sorted(next(os.walk(pathToImgFolder))[2]):
    if '.json' in x:
      with open(os.path.join(pathToImgFolder, x)) as json_file:
        data = json.load(json_file)
        for i in range(0, len(data["shapes"])):
          bodyContour   = np.array([data["shapes"][i]["points"]])
          originalShape = np.zeros((data["imageHeight"], data["imageWidth"]))
          originalShape[:, :] = 0
          originalShape = originalShape.astype(np.uint8)
          bodyContour = bodyContour.astype(np.int)
          cv2.fillPoly(originalShape, pts =[bodyContour], color=(1))
          cv2.imwrite(os.path.join(pathToMaskDir, x[:len(x)-5] + '_mask.png'), originalShape)






