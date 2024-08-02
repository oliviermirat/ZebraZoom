import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.preprocessImage import preprocessImage
import math
import json
import random
import os


def improveContrast(frame, hyperparameters):
  frame = 255 - frame
  frameIsBGR = len(frame.shape) == 3
  if frameIsBGR:
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  lowVal = int(np.quantile(frame, hyperparameters["outputValidationVideoContrastImprovementQuartile"]))
  highVal = int(np.quantile(frame, 1 - hyperparameters["outputValidationVideoContrastImprovementQuartile"]))
  frame[frame < lowVal] = lowVal
  frame[frame > highVal] = highVal
  frame = frame - lowVal
  mult = np.max(frame)
  frame = frame * (255 / mult)
  frame = frame.astype('uint8')
  if frameIsBGR:
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
  return frame


def calculateInfoFrameForFrame(superStruct, hyperparameters, wellIdx, animalIdx, boutIdx, frameIdx, colorModifTab):
  plotOnlyOneTailPointForVisu = hyperparameters["plotOnlyOneTailPointForVisu"]
  trackingPointSizeDisplay    = hyperparameters["trackingPointSizeDisplay"]
  infoWells = []
  
  for i in range(0, len(superStruct["wellPositions"])):
    x = superStruct["wellPositions"][i]["topLeftX"]
    y = superStruct["wellPositions"][i]["topLeftY"]
    infoWells.append([x, y])

  infoFrame = []
  if hyperparameters['extractAdvanceZebraParameters'] and ("Bend_TimingAbsolute" in superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]):
    Bend_TimingAbsolute = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["Bend_TimingAbsolute"]
  else:
    Bend_TimingAbsolute = []

  relativeFrameIdx = frameIdx - superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["BoutStart"]

  anglePointsBefore = []
  anglePointsBaseBefore = []
  x0 = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["HeadX"][0]
  y0 = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["HeadY"][0]

  x = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["HeadX"][relativeFrameIdx]
  y = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["HeadY"][relativeFrameIdx]
  Heading = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["Heading"][relativeFrameIdx] if "Heading" in superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx] else -10

  x = x + infoWells[wellIdx][0]
  y = y + infoWells[wellIdx][1]
  dataToPlot = {}
  dataToPlot["x"]       = x
  dataToPlot["y"]       = y
  dataToPlot["size"]    = trackingPointSizeDisplay + (0 if plotOnlyOneTailPointForVisu else 2)
  dataToPlot["Heading"] = Heading
  dataToPlot["numMouv"] = boutIdx+1
  dataToPlot["numWell"] = wellIdx
  dataToPlot["numAnimal"] = animalIdx

  dataToPlot["red"]     = 0
  dataToPlot["green"]   = 100
  dataToPlot["blue"]    = 255

  infoFrame.append(dataToPlot)

  # Points along the Tail
  nbPointsToPlot   = 0
  if plotOnlyOneTailPointForVisu:
    nbPointsToPlot = len(superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["TailX_VideoReferential"][relativeFrameIdx])
    pointsToPlot = (0, *range(nbPointsToPlot - 1, nbPointsToPlot))
  else:
    nbPointsToPlot = len(superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["TailX_VideoReferential"][relativeFrameIdx]) if "TailX_VideoReferential" in superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx] else 0
    pointsToPlot = range(nbPointsToPlot)

  for m in pointsToPlot:
    tailX = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["TailX_VideoReferential"][relativeFrameIdx][m]
    tailY = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["TailY_VideoReferential"][relativeFrameIdx][m]
    tailX = tailX + infoWells[wellIdx][0]
    tailY = tailY + infoWells[wellIdx][1]
    size = 1
    dataToPlot      = {}
    dataToPlot["x"] = tailX
    dataToPlot["y"] = tailY
    if (m == (nbPointsToPlot-1)):
      if (Bend_TimingAbsolute.count(frameIdx+1) != 0):
        dataToPlot["size"] = trackingPointSizeDisplay + (0 if plotOnlyOneTailPointForVisu else 5)
        dataToPlot["red"]   = 0
        dataToPlot["green"] = 0
        dataToPlot["blue"]  = 255
      else:
        dataToPlot["size"] = trackingPointSizeDisplay + (0 if plotOnlyOneTailPointForVisu else 2)
        dataToPlot["red"]   = 0
        dataToPlot["green"] = 255
        dataToPlot["blue"]  = 0
    else:
      dataToPlot["size"] = trackingPointSizeDisplay
      dataToPlot["red"]   = 0   + colorModifTab[animalIdx]["red"]
      dataToPlot["green"] = 255 - colorModifTab[animalIdx]["green"]
      dataToPlot["blue"]  = 0   + colorModifTab[animalIdx]["blue"]
    dataToPlot["Heading"] = -10

    infoFrame.append(dataToPlot)

  if hyperparameters["eyeTracking"] or "leftEyeX" in superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]:
    leftEyeX     = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["leftEyeX"][relativeFrameIdx]
    leftEyeY     = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["leftEyeY"][relativeFrameIdx]
    leftEyeAngle = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["leftEyeAngle"][relativeFrameIdx]
    leftEyeX = leftEyeX + infoWells[wellIdx][0]
    leftEyeY = leftEyeY + infoWells[wellIdx][1]
    dataToPlot = {}
    dataToPlot["x"]       = leftEyeX
    dataToPlot["y"]       = leftEyeY
    dataToPlot["size"]    = 1
    dataToPlot["Heading"] = leftEyeAngle
    dataToPlot["headingColor"] = (0, 255, 0)
    dataToPlot["headingWidth"]    = 2 # hyperparameters["eyeTrackingHeadEmbeddedWidth"]
    dataToPlot["headingHalfDiam"] = hyperparameters["eyeTrackingHeadEmbeddedHalfDiameter"]
    dataToPlot["numMouv"] = boutIdx+1
    dataToPlot["numWell"] = wellIdx
    dataToPlot["red"]     = 255
    dataToPlot["green"]   = 255
    dataToPlot["blue"]    = 0
    infoFrame.append(dataToPlot)

    rightEyeX     = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["rightEyeX"][relativeFrameIdx]
    rightEyeY     = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["rightEyeY"][relativeFrameIdx]
    rightEyeAngle = superStruct["wellPoissMouv"][wellIdx][animalIdx][boutIdx]["rightEyeAngle"][relativeFrameIdx]
    rightEyeX = rightEyeX + infoWells[wellIdx][0]
    rightEyeY = rightEyeY + infoWells[wellIdx][1]
    dataToPlot = {}
    dataToPlot["x"]       = rightEyeX
    dataToPlot["y"]       = rightEyeY
    dataToPlot["size"]    = 1
    dataToPlot["Heading"] = rightEyeAngle
    dataToPlot["headingColor"] = (0, 255, 0)
    dataToPlot["headingWidth"]    = 2 # hyperparameters["eyeTrackingHeadEmbeddedWidth"]
    dataToPlot["headingHalfDiam"] = hyperparameters["eyeTrackingHeadEmbeddedHalfDiameter"]
    # dataToPlot["numMouv"] = boutIdx+1
    # dataToPlot["numWell"] = wellIdx
    dataToPlot["red"]     = 0
    dataToPlot["green"]   = 0
    dataToPlot["blue"]    = 255
    infoFrame.append(dataToPlot)
  return infoFrame

def calculateInfoFrame(superStruct, hyperparameters, nbFrames, colorModifTab):
  infoFrame = [[] for _ in range(nbFrames)]

  for i in range(0, len(superStruct["wellPoissMouv"])):
    for j in range(0, len(superStruct["wellPoissMouv"][i])):
      for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
        BoutStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
        BoutEnd = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]
        mouvLength = len(superStruct["wellPoissMouv"][i][j][k]["HeadX"])
        for l in range(BoutStart, min(BoutEnd + 1, nbFrames)):
          infoFrame[l].extend(calculateInfoFrameForFrame(superStruct, hyperparameters, i, j, k, l, colorModifTab))
  return infoFrame


def drawInfoFrame(frame, infoFrame, colorModifTab, hyperparameters):
  for data in infoFrame:
    x = data["x"]
    y = data["y"]
    size  = data["size"]
    red   = data["red"]
    green = data["green"]
    blue  = data["blue"]
    if (data["Heading"] != -10):
      heading = data["Heading"]
      headingColor = data["headingColor"] if "headingColor" in data else (255,0,0)
      headingWidth = data["headingWidth"] if "headingWidth" in data else hyperparameters["trackingPointSizeDisplay"]
      headingHalfDiam = data["headingHalfDiam"] if "headingHalfDiam" in data else 20
      if hyperparameters["validationVideoPlotHeading"] and not(np.isnan(x)) and not(np.isnan(y)) and not(np.isnan(heading)):
        if hyperparameters["debugValidationVideoHeading"] == 0:
          cv2.line(frame,(int(x),int(y)),(int(x+headingHalfDiam*math.cos(heading)),int(y+headingHalfDiam*math.sin(heading))), headingColor, headingWidth)
        else:
          cv2.line(frame,(int(x),int(y)),(int(x-250*math.cos(heading)),int(y-250*math.sin(heading))), headingColor, headingWidth)

      # if ("numMouv" in data) and ("numWell" in data):
        # numMouv = data["numMouv"]
        # numWell = data["numWell"]
        # cv2.putText(frame,str(numMouv),(15+infoWells[numWell][0],25+infoWells[numWell][1]),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255))
    
    if x != float('nan') and y != float('nan') and not(math.isnan(x)) and not(math.isnan(y)):
      cv2.circle(frame, (int(x),int(y)), size, (red,green,blue), -1)

    if hyperparameters["validationVideoPlotAnimalNumber"]:
      if "numAnimal" in data:
        numAnimal = int(data["numAnimal"])
        red       = int(0   + colorModifTab[numAnimal]["red"])
        green     = int(255 - colorModifTab[numAnimal]["green"])
        blue      = int(0   + colorModifTab[numAnimal]["blue"])
        cv2.putText(frame, str(numAnimal), (int(x + 10), int(y + 10)), cv2.FONT_HERSHEY_SIMPLEX, 1, (red, green, blue), 2)


def processFrame(frame, hyperparameters, infoFrame, colorModifTab):
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)

  if hyperparameters["reduceImageResolutionPercentage"]:
    frame_height, frame_width = frame.shape[:2]
    frame = cv2.resize(frame, (int(frame_width * hyperparameters["reduceImageResolutionPercentage"]), int(frame_height * hyperparameters["reduceImageResolutionPercentage"])), interpolation = cv2.INTER_AREA)
  if hyperparameters["outputValidationVideoContrastImprovement"]:
    frame = improveContrast(frame, hyperparameters)

  drawInfoFrame(frame, infoFrame, colorModifTab, hyperparameters)
  return frame


def createValidationVideo(videoPath, superStruct, hyperparameters, outputName=None):

  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("Starting the creation of the validation video")

  firstFrame                  = hyperparameters["firstFrame"]
  lastFrame                   = hyperparameters["lastFrame"]

  cap = zzVideoReading.VideoCapture(videoPath, hyperparameters)
  if (cap.isOpened() == False):
    print("Error opening video stream or file")

  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  nbFrames     = int(cap.get(7))
  inputFps     = int(cap.get(5))

  colorModifTab = [{"red": random.randrange(255), "green": random.randrange(255), "blue": random.randrange(255)} for i in range(1, hyperparameters["nbAnimalsPerWell"])]
  colorModifTab.insert(0, {"red": 0, "green": 0, "blue": 0})
  infoFrame = calculateInfoFrame(superStruct, hyperparameters, nbFrames, colorModifTab)
            
  # Going through the video and printing stuff on it.
  outputFps = inputFps
  if hyperparameters["outputValidationVideoFps"] > 0:
    outputFps = int(hyperparameters["outputValidationVideoFps"])
  
  out = cv2.VideoWriter(outputName,cv2.VideoWriter_fourcc('M','J','P','G'), outputFps, (int(frame_width * hyperparameters["reduceImageResolutionPercentage"]), int(frame_height * hyperparameters["reduceImageResolutionPercentage"])))
  
  if int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
    lastFrame = min(lastFrame, firstFrame + int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
  
  cap.set(1, firstFrame)
  
  for l in range(firstFrame, lastFrame):
  
    if l < nbFrames:
    
      if (hyperparameters["freqAlgoPosFollow"] != 0) and (l % hyperparameters["freqAlgoPosFollow"] == 0):
        print("Validation video creation: frame:", l)
    
      ret, frame = cap.read()
      if not ret:
        continue

      frame = processFrame(frame, hyperparameters, infoFrame[l], colorModifTab)
      out.write(frame)
  
  out.release()
  
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("Validation video created")
  if hyperparameters["popUpAlgoFollow"]:
    import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

    popUpAlgoFollow.prepend("Create Validation Video")

  return infoFrame


def createSmallValidationVideosForFlagged(resultFolderPath, offset):
  videoName = os.path.basename(resultFolderPath)
  expectedResultsFile = os.path.join(resultFolderPath, 'results_%s.txt' % videoName)
  if os.path.exists(expectedResultsFile):
    resultsFile = expectedResultsFile
  else:
    if not os.path.exists(resultFolderPath):
      raise ValueError('path %s does not exist' % resultFolderPath)
    resultsFile = next((f for f in os.listdir(resultFolderPath) if os.path.isfile(os.path.join(resultFolderPath, f)) and f.startswith('results_')), None)
    if resultsFile is None:
      raise ValueError('folder %s does not contain the results file' % resultFolderPath)
    resultsFile = os.path.join(resultFolderPath, resultsFile)
  with open(resultsFile) as f:
    supstruct = json.load(f)
  wellPositions = [(max(well["topLeftX"], 0), max(well["topLeftY"], 0), well["lengthX"], well["lengthY"]) for well in supstruct["wellPositions"]]
  flaggedBouts = [(wellIdx, animalIdx, boutIdx, bout["BoutStart"] - offset, bout["BoutEnd"] + offset) for wellIdx, well in enumerate(supstruct["wellPoissMouv"]) for animalIdx, animal in enumerate(well) for boutIdx, bout in enumerate(animal) if bout.get("flag", False)]

  expectedVideoFile = os.path.join(resultFolderPath, '%s.avi' % videoName)
  if os.path.exists(expectedVideoFile):
    videoPath = expectedVideoFile
  else:
    videoFile = next((f for f in os.listdir(resultFolderPath) if os.path.isfile(os.path.join(resultFolderPath, f)) and f.endswith('.avi')), None)
    if videoFile is None:
      raise ValueError('folder %s does not contain the validation video' % resultFolderPath)
    videoPath = os.path.join(resultFolderPath, videoFile)
  cap = zzVideoReading.VideoCapture(videoPath)
  if not cap.isOpened():
    raise ValueError("could not open video file %s" % videoPath)

  outputDirectory = os.path.join(resultFolderPath, 'flaggedBouts')
  if not os.path.exists(outputDirectory):
    os.mkdir(outputDirectory)
  for subvideoIdx, (wellIdx, animalIdx, boutIdx, firstFrame, lastFrame) in enumerate(flaggedBouts):
    frameIdx = max(0, firstFrame)
    x, y, width, height = wellPositions[wellIdx]
    writer = cv2.VideoWriter(os.path.join(outputDirectory, '%s_well%d_animal%d_bout%d.avi' % (videoName, wellIdx, animalIdx, boutIdx)), cv2.VideoWriter_fourcc('M','J','P','G'), 10, (width, height))
    cap.set(1, frameIdx)
    while cap.isOpened() and frameIdx < lastFrame:
      frameIdx += 1
      ret, frame = cap.read()
      if not ret:
        continue
      writer.write(frame[y:y+height,x:x+width])
    writer.release()
  cap.release()
  print('No flagged bouts found in the results.' if not flaggedBouts else 'Subvideos created in %s' % outputDirectory)
