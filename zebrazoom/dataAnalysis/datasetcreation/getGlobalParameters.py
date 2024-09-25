from zebrazoom.dataAnalysis.datasetcreation.getDeltaHead import getDeltaHead
import numpy as np
from scipy.interpolate import UnivariateSpline
import math

def getGlobalParameters(curbout, fps, pixelSize, frameStepForDistanceCalculation, previousBoutEnd, listOfParametersToCalculate, firstFrame, lastFrame, minimumFrameToFrameDistanceToBeConsideredAsMoving=0):
  
  listOfParametersCalculated = []
  
  for parameterToCalculate in listOfParametersToCalculate:
    
    
    
    if parameterToCalculate == 'Bout Duration (s)':
      
      BoutDuration = (curbout["BoutEnd"] - curbout["BoutStart"] + 1) / fps
      listOfParametersCalculated.append(BoutDuration)
    
    
    
    elif parameterToCalculate == 'Bout Distance (mm)':
      
      TotalDistance = 0
      posX = curbout["HeadX"]
      posY = curbout["HeadY"]
      rangeUsedForDistanceCalculation   = [frameStepForDistanceCalculation*i for i in range(0, int(len(posX)/frameStepForDistanceCalculation))]
      if len(rangeUsedForDistanceCalculation) == 0:
        rangeUsedForDistanceCalculation = [0, len(posX) - 1]
      else:
        rangeUsedForDistanceCalculation = rangeUsedForDistanceCalculation + [len(posX) - 1]
      # if removeLargeInstantaneousDistanceData is set, then some nan values may be present which we must propogate for frameStepForDistanceCalculation frames to enable the discarding of frame below
      for i in range(frameStepForDistanceCalculation, len(posX)):
        if np.isnan(posX[i]) or np.isnan(posY[i]):
          for j in range(i - frameStepForDistanceCalculation, i):
            posX[j] = float('nan')
            posY[j] = float('nan')
      posX = [posX[i] for i in rangeUsedForDistanceCalculation]
      posY = [posY[i] for i in rangeUsedForDistanceCalculation]
      # if removeLargeInstantaneousDistanceData is set, we must discard the nan frames as they correspond to "jumps"
      countNotTakingIntoAccount = 0
      for j in range(0, len(posX)-1):
        if not(np.isnan(posX[j+1])) and not(np.isnan(posX[j])) and not(np.isnan(posY[j+1])) and not(np.isnan(posY[j])):
          TotalDistance = TotalDistance + math.sqrt((posX[j+1] - posX[j])**2 + (posY[j+1] - posY[j])**2)
        else:
          countNotTakingIntoAccount = countNotTakingIntoAccount + 1
      TotalDistance = TotalDistance * pixelSize
      if countNotTakingIntoAccount != 0:
        takingIntoAccount = len(posX) - 1 - countNotTakingIntoAccount
        TotalDistance = TotalDistance * ((len(posX) - 1) / takingIntoAccount)
      listOfParametersCalculated.append(TotalDistance)
    
    
    elif parameterToCalculate == 'Angular Velocity (deg/s)':
      
      if ("Heading" in curbout) and (len(curbout["Heading"]) > 1):
        heading = curbout["Heading"]
        posX = curbout["HeadX"]
        posY = curbout["HeadY"]
        rangeUsedForDistanceCalculation   = [frameStepForDistanceCalculation*i for i in range(0, int(len(heading)/frameStepForDistanceCalculation))]
        if len(rangeUsedForDistanceCalculation) == 0:
          rangeUsedForDistanceCalculation = [0, len(heading) - 1]
        else:
          rangeUsedForDistanceCalculation = rangeUsedForDistanceCalculation + [len(heading) - 1]
        # if removeLargeInstantaneousDistanceData is set, then some nan values may be present which we must propogate for frameStepForDistanceCalculation frames to enable the discarding of frame below
        for i in range(frameStepForDistanceCalculation, len(heading)):
          if np.isnan(heading[i]) or np.isnan(posX[i]) or np.isnan(posY[i]):
            for j in range(i - frameStepForDistanceCalculation, i + 1):
              heading[j] = float('nan')
        heading = [heading[i] for i in rangeUsedForDistanceCalculation]
        # if removeLargeInstantaneousDistanceData is set, we must discard the nan frames as they correspond to "jumps"
        angularDifferential = []
        for j in range(0, len(heading)-1):
          if not(np.isnan(heading[j+1])) and not(np.isnan(heading[j])):
            angularDifferential = angularDifferential + [(min(abs((heading[j+1] - heading[j]) * (180 / np.pi)) % 180, abs((heading[j+1] - heading[j] + 2 * np.pi) * (180 / np.pi)) % 180, abs((heading[j+1] - heading[j] - 2 * np.pi) * (180 / np.pi)) % 180)) / (frameStepForDistanceCalculation / fps)]
        listOfParametersCalculated.append(np.mean(angularDifferential) if angularDifferential else 0)
      else:
        listOfParametersCalculated.append(0)
    
    elif parameterToCalculate == 'maxInstantaneousSpeed':
      
      posX = curbout["HeadX"]
      posY = curbout["HeadY"]
      instantaneousSpeed = []
      for j in range(0, len(posX)-1):
        instantaneousSpeed.append(math.sqrt((posX[j+1] - posX[j])**2 + (posY[j+1] - posY[j])**2) * pixelSize * fps)
      if len(instantaneousSpeed):
        listOfParametersCalculated.append(np.max(instantaneousSpeed))
      else:
        listOfParametersCalculated.append(0)
    
    
    elif parameterToCalculate == 'percentOfMovingFramesBasedOnDistance':
      
      posX = curbout["HeadX"]
      posY = curbout["HeadY"]
      # rangeUsedForDistanceCalculation   = [frameStepForDistanceCalculation*i for i in range(0, int(len(posX)/frameStepForDistanceCalculation))]
      # if len(rangeUsedForDistanceCalculation) == 0:
        # rangeUsedForDistanceCalculation = [0, len(posX) - 1]
      # else:
        # rangeUsedForDistanceCalculation = rangeUsedForDistanceCalculation + [len(posX) - 1]
      # posX = [posX[i] for i in rangeUsedForDistanceCalculation]
      # posY = [posY[i] for i in rangeUsedForDistanceCalculation]
      distance = np.array([math.sqrt((posX[j+1] - posX[j])**2 + (posY[j+1] - posY[j])**2) * pixelSize for j in range(0, len(posX)-1)])
      numberOfMovingFrames   = int(np.sum(distance > minimumFrameToFrameDistanceToBeConsideredAsMoving))
      percentOfMovingFrames = (numberOfMovingFrames / (lastFrame - firstFrame + 1)) * 100
      listOfParametersCalculated.append(percentOfMovingFrames)
    
    
    
    elif parameterToCalculate == 'Bout Speed (mm/s)':
      
      Speed = TotalDistance * fps / (curbout["BoutEnd"] - curbout["BoutStart"]) # This is a bit of a "hack" (not very "clean"), it only works because the listOfParametersToCalculate provided contains TotalDistance before Speed
      listOfParametersCalculated.append(Speed)
    
    
    
    elif parameterToCalculate == 'Number of Oscillations':
      
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list:
        NumberOfOscillations = len(curbout["Bend_Timing"]) / 2
      else:
        NumberOfOscillations = float('NaN')
      listOfParametersCalculated.append(NumberOfOscillations)
    
    
    
    elif parameterToCalculate == 'meanTBF':
      meanTBF = NumberOfOscillations / BoutDuration # This is a bit of a "hack" (not very "clean"), it only works because the listOfParametersToCalculate provided contains NumberOfOscillations and BoutDuration before meanTBF
      listOfParametersCalculated.append(meanTBF)
    
    
    
    elif parameterToCalculate == 'Max TBF (Hz)':
      
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]):
        maxOfInstantaneousTBF = np.max(fps / (2 * np.diff([0] + curbout['Bend_Timing'])))
      else:
        maxOfInstantaneousTBF = float('NaN')
      listOfParametersCalculated.append(maxOfInstantaneousTBF)
    
    
    
    elif parameterToCalculate == 'Mean TBF (Hz)':
      
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]):
        meanOfInstantaneousTBF = np.mean(fps / (2 * np.diff([0] + curbout['Bend_Timing'])))
      else:
        meanOfInstantaneousTBF = float('NaN')
      listOfParametersCalculated.append(meanOfInstantaneousTBF)
    
    
    
    elif parameterToCalculate == 'medianOfInstantaneousTBF':
      
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]):
        medianOfInstantaneousTBF = np.median(fps / (2 * np.diff([0] + curbout['Bend_Timing'])))
      else:
        medianOfInstantaneousTBF = float('NaN')
      listOfParametersCalculated.append(medianOfInstantaneousTBF)
    
    
    
    elif parameterToCalculate == 'Mean TBF (Hz) (based on first 4 bends)':
      
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]):
        if len(curbout['Bend_Timing']) >= 4:
          first4Bends = curbout['Bend_Timing'][:4]
        else:
          first4Bends = curbout['Bend_Timing']
        meanOfInstantaneousTBFfirst4Bends = np.mean(fps / (2 * np.diff([0] + first4Bends)))
      else:
        meanOfInstantaneousTBFfirst4Bends = float('NaN')
      listOfParametersCalculated.append(meanOfInstantaneousTBFfirst4Bends)
    
    
    
    elif parameterToCalculate == 'Mean TBF (Hz) (based on first 6 bends)':
      
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]):
        if len(curbout['Bend_Timing']) >= 6:
          first6Bends = curbout['Bend_Timing'][:6]
        else:
          first6Bends = curbout['Bend_Timing']
        meanOfInstantaneousTBFfirst6Bends = np.mean(fps / (2 * np.diff([0] + first6Bends)))
      else:
        meanOfInstantaneousTBFfirst6Bends = float('NaN')
      listOfParametersCalculated.append(meanOfInstantaneousTBFfirst6Bends)
    
    
    
    elif parameterToCalculate == 'Max absolute TBA (deg.)':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        maxBendAmplitude = max(list(map(abs, curbout["Bend_Amplitude"]))) * (180 / math.pi)
      else:
        maxBendAmplitude = float('NaN')
      listOfParametersCalculated.append(maxBendAmplitude)
    
    
    
    elif parameterToCalculate == 'maxBendAmplitudeSigned':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        maxBendAmplitudeSigned = curbout["Bend_Amplitude"][np.argmax(abs(np.array(curbout["Bend_Amplitude"])))] * (180 / math.pi)
      else:
        maxBendAmplitudeSigned = float('NaN')
      listOfParametersCalculated.append(maxBendAmplitudeSigned)
    
    
    
    elif parameterToCalculate == 'Median absolute TBA (deg.)':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        medianBendAmplitude = np.median(list(map(abs, curbout["Bend_Amplitude"]))) * (180 / math.pi)
      else:
        medianBendAmplitude = float('NaN')
      listOfParametersCalculated.append(medianBendAmplitude)



    elif parameterToCalculate == 'medianBendAmplitudeSigned':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        medianBendAmplitudeSigned = np.median(curbout["Bend_Amplitude"]) * (180 / math.pi)
      else:
        medianBendAmplitudeSigned = float('NaN')
      listOfParametersCalculated.append(medianBendAmplitudeSigned)



    elif parameterToCalculate == 'Mean absolute TBA (deg.)':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        meanBendAmplitude = np.mean(list(map(abs, curbout["Bend_Amplitude"]))) * (180 / math.pi)
      else:
        meanBendAmplitude = float('NaN')
      listOfParametersCalculated.append(meanBendAmplitude)
    
    
    
    elif parameterToCalculate == 'maxTailAngleAmplitude':
      
      if "TailAngle_smoothed" in curbout and len(curbout["TailAngle_smoothed"]):
        maxAmplitude = max([abs(ta) for ta in curbout["TailAngle_smoothed"]]) * (180 / math.pi)
      else:
        if "TailAngle_Raw" in curbout and len(curbout["TailAngle_Raw"]):
          maxAmplitude = max([abs(ta) for ta in curbout["TailAngle_Raw"]]) * (180 / math.pi) # Maybe this value should be "reduced" in some way to be consistent with the previous smoothed tail angle
        else:
          maxAmplitude = float('NaN')
      listOfParametersCalculated.append(maxAmplitude)



    elif parameterToCalculate == 'binaryClass25degMaxTailAngle': # Kind of a hack again as it relies on maxAmplitude having been calculated previously
      
      if maxAmplitude != float('NaN'):
        binaryClass25degMaxTailAngle = 0 if maxAmplitude <= 25 else 1
      else:
        binaryClass25degMaxTailAngle = float('NaN')
        
      listOfParametersCalculated.append(binaryClass25degMaxTailAngle)    
    
    
    
    elif parameterToCalculate == 'Absolute Yaw (deg)':
      
      deltahead  = abs(getDeltaHead(curbout))
      listOfParametersCalculated.append(deltahead)
    
    elif parameterToCalculate == 'Signed Yaw (deg)':
      deltahead  = getDeltaHead(curbout)
      listOfParametersCalculated.append(deltahead)


    elif parameterToCalculate == 'Absolute Yaw (deg) (from heading vals)':
      
      deltahead  = abs(getDeltaHead(curbout, fromHeadingIdx=-1))
      listOfParametersCalculated.append(deltahead)
    
    elif parameterToCalculate == 'Signed Yaw (deg) (from heading vals)':
      deltahead  = getDeltaHead(curbout, fromHeadingIdx=-1)
      listOfParametersCalculated.append(deltahead)


    elif parameterToCalculate == 'headingRangeWidth':
      deltas = [getDeltaHead(curbout, fromHeadingIdx=idx) for idx in range(1, curbout["BoutEnd"] - curbout["BoutStart"] + 1)]
      deltas.append(0)
      listOfParametersCalculated.append(max(deltas) - min(deltas))

    elif parameterToCalculate == 'xstart':
      
      posX = curbout["HeadY"]
      if len(posX) >= 1:
        xstart = posX[0] * pixelSize
      else:
        xstart = 0
      listOfParametersCalculated.append(xstart)
    
    
    
    elif parameterToCalculate == 'xend':
      
      posX = curbout["HeadX"]
      if len(posX) >= 1:
        xend = posX[len(posX)-1] * pixelSize
      else:
        xend = 0
      listOfParametersCalculated.append(xend)
    
    
    
    elif parameterToCalculate == 'xmean':
      
      posX = curbout["HeadX"]
      if len(posX) >= 1:
        xmean = np.mean(posX) * pixelSize
      else:
        xmean = 0
      listOfParametersCalculated.append(xmean)



    elif parameterToCalculate == 'ymean':
      
      posY = curbout["HeadY"]
      if len(posY) >= 1:
        ymean = np.mean(posY) * pixelSize
      else:
        ymean = 0
      listOfParametersCalculated.append(ymean)      
    
    
    
    elif parameterToCalculate == 'TBA#1 timing (s)':
    
      if "Bend_Timing" in curbout and type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]):
        firstBendTime = curbout["Bend_Timing"][0] / fps
      else:
        firstBendTime = float('NaN')  
      listOfParametersCalculated.append(firstBendTime)
    
    
    
    elif parameterToCalculate == 'TBA#1 Amplitude (deg)':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        firstBendAmplitude = abs(curbout["Bend_Amplitude"][0]) * (180 / math.pi)
      else:
        firstBendAmplitude = float('NaN')
      listOfParametersCalculated.append(firstBendAmplitude)



    elif parameterToCalculate == 'firstBendAmplitudeSigned':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]):
        firstBendAmplitudeSigned = curbout["Bend_Amplitude"][0] * (180 / math.pi)
      else:
        firstBendAmplitudeSigned = float('NaN')
      listOfParametersCalculated.append(firstBendAmplitudeSigned)



    elif parameterToCalculate == 'IBI (s)':
      
      IBI = (curbout["BoutStart"] - previousBoutEnd) / fps
      listOfParametersCalculated.append(IBI)
    
    

    elif parameterToCalculate == 'BoutFrameNumberStart':
      
      BoutFrameNumberStart = curbout["BoutStart"]
      listOfParametersCalculated.append(BoutFrameNumberStart)
    
    
    
    elif parameterToCalculate == 'tailAngleSymmetry':
      if "TailAngle_smoothed" in curbout and len(curbout["TailAngle_smoothed"]):
        TailAngle = curbout["TailAngle_smoothed"]
      else:
        if "TailAngle_Raw" in curbout and len(curbout["TailAngle_Raw"]):
          TailAngle = curbout["TailAngle_Raw"]
        else:
          TailAngle = []
      maxTailAngle = max(TailAngle) if len(TailAngle) else 0
      minTailAngle = min(TailAngle) if len(TailAngle) else 0
      if abs(maxTailAngle) < abs(minTailAngle):
        TailAngle = [-elem for elem in TailAngle]
      maxTailAngle = max(TailAngle) if len(TailAngle) else 0
      minTailAngle = min(TailAngle) if len(TailAngle) else 0
      tailAngleSymmetry = - minTailAngle / maxTailAngle if maxTailAngle > 0 else 1
      # = 1 if perfect symetry OR if tail angle staying constant and always at 0
      # = 0 if tail beating only on one side, starting from the 0 position
      # < 0 but > -1 if tail beating only on one side, starting from the side it's beating (not from 0)
      listOfParametersCalculated.append(tailAngleSymmetry)
    
    
    
    elif parameterToCalculate == 'secondBendAmpDividedByFirst':
      
      if "Bend_Amplitude" in curbout and type(curbout["Bend_Amplitude"]) == list and len(curbout["Bend_Amplitude"]) >= 2 and curbout["Bend_Amplitude"][0]:
        secondBendAmpDividedByFirst = curbout["Bend_Amplitude"][1] / curbout["Bend_Amplitude"][0]
      else:
        secondBendAmpDividedByFirst = float('Nan')
      listOfParametersCalculated.append(secondBendAmpDividedByFirst)
    
    
    
    elif parameterToCalculate == 'tailAngleIntegral':
      
      if "TailAngle_smoothed" in curbout and len(curbout["TailAngle_smoothed"]):
        tailAngleIntegral = np.sum([abs(ta) for ta in curbout["TailAngle_smoothed"]]) * (180 / math.pi)
      else:
        if "TailAngle_Raw" in curbout and len(curbout["TailAngle_Raw"]):
          tailAngleIntegral = np.sum([abs(ta) for ta in curbout["TailAngle_Raw"]]) * (180 / math.pi) # Maybe this value should be "reduced" in some way to be consistent with the previous smoothed tail angle
        else:
          tailAngleIntegral = float('NaN')
      listOfParametersCalculated.append(tailAngleIntegral)



    elif parameterToCalculate == 'tailAngleIntegralSigned':
      
      if "TailAngle_smoothed" in curbout and len(curbout["TailAngle_smoothed"]):
        tailAngleIntegral = np.sum([ta for ta in curbout["TailAngle_smoothed"]]) * (180 / math.pi)
      else:
        if "TailAngle_Raw" in curbout and len(curbout["TailAngle_Raw"]):
          tailAngleIntegral = np.sum([ta for ta in curbout["TailAngle_Raw"]]) * (180 / math.pi) # Maybe this value should be "reduced" in some way to be consistent with the previous smoothed tail angle
        else:
          tailAngleIntegral = float('NaN')
      listOfParametersCalculated.append(tailAngleIntegral)



    else:
      
      print("The parameter", parameterToCalculate, "is not specified")
      break;
      
    # elif parameterToCalculate == '':
      # listOfParametersCalculated.append()
  
  return listOfParametersCalculated