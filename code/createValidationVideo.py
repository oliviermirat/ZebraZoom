import numpy as np
import cv2
import math
import json
import popUpAlgoFollow
import random

def createValidationVideo(videoPath, superStruct, hyperparameters):

  firstFrame                  = hyperparameters["firstFrame"]
  lastFrame                   = hyperparameters["lastFrame"]
  plotOnlyOneTailPointForVisu = hyperparameters["plotOnlyOneTailPointForVisu"]
  trackingPointSizeDisplay    = hyperparameters["trackingPointSizeDisplay"]
  
  cap = cv2.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")

  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  nbFrames     = int(cap.get(7))
  
  infoFrame = [[]] * nbFrames
  infoWells = []
  
  for i in range(0, len(superStruct["wellPositions"])):
    x = superStruct["wellPositions"][i]["topLeftX"]
    y = superStruct["wellPositions"][i]["topLeftY"]
    infoWells.append([x, y])
  
  for i in range(0, len(superStruct["wellPoissMouv"])):
    colorModifTab = [{"red": random.randrange(255), "green": random.randrange(255), "blue": random.randrange(255)} for i in range(1, hyperparameters["nbAnimalsPerWell"])]
    colorModifTab.insert(0, {"red": 0, "green": 0, "blue": 0})
    # colorModifTab.insert(0, {"red": 0, "green": 0, "blue": 0})
    for j in range(0, len(superStruct["wellPoissMouv"][i])):
      for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
      
        BoutStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
        BoutEnd = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]
        mouvLength = len(superStruct["wellPoissMouv"][i][j][k]["HeadX"])
        if hyperparameters['extractAdvanceZebraParameters']:
          Bend_TimingAbsolute = superStruct["wellPoissMouv"][i][j][k]["Bend_TimingAbsolute"]
        else:
          Bend_TimingAbsolute = []
        
        anglePointsBefore = []
        anglePointsBaseBefore = []
        x0 = superStruct["wellPoissMouv"][i][j][k]["HeadX"][0]
        y0 = superStruct["wellPoissMouv"][i][j][k]["HeadY"][0]
        for l in range(0,mouvLength):
          if BoutStart + l < nbFrames:
            x = superStruct["wellPoissMouv"][i][j][k]["HeadX"][l]
            y = superStruct["wellPoissMouv"][i][j][k]["HeadY"][l]
            Heading = superStruct["wellPoissMouv"][i][j][k]["Heading"][l]
            
            x = x + infoWells[i][0]
            y = y + infoWells[i][1]
            dataToPlot = {}
            dataToPlot["x"]       = x
            dataToPlot["y"]       = y
            dataToPlot["size"]    = trackingPointSizeDisplay + 2
            dataToPlot["Heading"] = Heading
            dataToPlot["numMouv"] = k+1
            dataToPlot["numWell"] = i
            
            dataToPlot["red"]     = 255
            dataToPlot["green"]   = 0
            dataToPlot["blue"]    = 0
            
            t = infoFrame[BoutStart + l]
            t2 = t.copy()
            t2.append(dataToPlot)
            infoFrame[BoutStart + l] = t2
            
            # Points along the Tail
            nbPointsToPlot   = 0
            firstPointToPlot = 0
            if plotOnlyOneTailPointForVisu:
              firstPointToPlot = len(superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"][l]) - 1
              nbPointsToPlot   = len(superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"][l])
            else:
              firstPointToPlot = 0
              nbPointsToPlot = len(superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"][l])
            
            for m in range(firstPointToPlot, nbPointsToPlot):
              tailX = superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"][l][m]
              tailY = superStruct["wellPoissMouv"][i][j][k]["TailY_VideoReferential"][l][m]
              tailX = tailX + infoWells[i][0]
              tailY = tailY + infoWells[i][1]
              size = 1
              dataToPlot      = {}
              dataToPlot["x"] = tailX
              dataToPlot["y"] = tailY
              if plotOnlyOneTailPointForVisu:
                if (Bend_TimingAbsolute.count(BoutStart+l+1) != 0):
                  dataToPlot["size"] = trackingPointSizeDisplay + 5
                  dataToPlot["red"]   = 0
                  dataToPlot["green"] = 0
                  dataToPlot["blue"]  = 255
                else:
                  dataToPlot["size"] = trackingPointSizeDisplay + 2
                  dataToPlot["red"]   = 0
                  dataToPlot["green"] = 255
                  dataToPlot["blue"]  = 0
              else:
                if (m == (nbPointsToPlot-1)):
                  if (Bend_TimingAbsolute.count(BoutStart+l+1) != 0):
                    dataToPlot["size"] = trackingPointSizeDisplay + 5
                    dataToPlot["red"]   = 0
                    dataToPlot["green"] = 0
                    dataToPlot["blue"]  = 255
                  else:
                    dataToPlot["size"] = trackingPointSizeDisplay + 2
                    dataToPlot["red"]   = 0
                    dataToPlot["green"] = 255
                    dataToPlot["blue"]  = 0
                else:
                  dataToPlot["size"] = trackingPointSizeDisplay;
                  dataToPlot["red"]   = 0   + colorModifTab[j]["red"]
                  dataToPlot["green"] = 255 - colorModifTab[j]["green"]
                  dataToPlot["blue"]  = 0   + colorModifTab[j]["blue"]
              dataToPlot["Heading"] = -10
              
              t = infoFrame[BoutStart + l]
              t2 = t.copy()
              t2.append(dataToPlot)
              infoFrame[BoutStart + l] = t2

  # Going through the video and printing stuff on it.
  outputName = hyperparameters["outputFolder"] + hyperparameters["videoName"] + '/' + hyperparameters["videoName"] + '.avi'
  out = cv2.VideoWriter(outputName,cv2.VideoWriter_fourcc('M','J','P','G'), 10, (frame_width,frame_height))

  cap.set(1, firstFrame)
  
  for l in range(firstFrame, lastFrame):
  
    if l < nbFrames:
      # cap.set(1, l)
      ret, frame = cap.read()
      
      for i in range(0, len(infoFrame[l])):
        x = infoFrame[l][i]["x"]
        y = infoFrame[l][i]["y"]
        size  = infoFrame[l][i]["size"]
        red   = infoFrame[l][i]["red"]
        green = infoFrame[l][i]["green"]
        blue  = infoFrame[l][i]["blue"]
        if (infoFrame[l][i]["Heading"] != -10):
          heading = infoFrame[l][i]["Heading"]
          if hyperparameters["validationVideoPlotHeading"]:
            if hyperparameters["debugValidationVideoHeading"] == 0:
              cv2.line(frame,(int(x),int(y)),(int(x+20*math.cos(heading)),int(y+20*math.sin(heading))), (255,0,0), trackingPointSizeDisplay+1)
            else:
              cv2.line(frame,(int(x),int(y)),(int(x-250*math.cos(heading)),int(y-250*math.sin(heading))), (255,0,0), trackingPointSizeDisplay+1)
          
          font = cv2.FONT_HERSHEY_SIMPLEX
          numMouv = infoFrame[l][i]["numMouv"]
          numWell = infoFrame[l][i]["numWell"]
          cv2.putText(frame,str(numMouv),(15+infoWells[numWell][0],25+infoWells[numWell][1]),font,1,(255,255,255))
          
          # CvFont font;
          # cvInitFont( &font, CV_FONT_HERSHEY_SIMPLEX,0.7,0.7,0,2,8);
          # std::ostringstream out;
          # out << infoFrame[l][i]["numMouv"];
          # string str = out.str();
          # size_t size = str.size() + 1;
          # char * buffer = new char[ size ];
          # strncpy( buffer, str.c_str(), size );
          # int numWell = (int) infoFrame[l][i]["numWell"];
          # cvRectangle(dst,cvPoint((int)infoWells[numWell][0],(int)infoWells[numWell][1]),cvPoint(15 + (int)infoWells[numWell][0], 25 + (int)infoWells[numWell][1]),CV_RGB(0,0,255),-1);
          # cvPutText(dst,buffer,cvPoint((int)infoWells[numWell][0],20+(int)infoWells[numWell][1]),&font,CV_RGB(255,255,255));

        cv2.circle(frame, (int(x),int(y)), size, (red,green,blue), -1)
        
      # cv2.imshow('Frame', frame)
      # cv2.waitKey(10)
      out.write(frame)
      
      # l = l + 1
  
  out.release()
  
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("Create Validation Video")
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Create Validation Video")

  return infoFrame
