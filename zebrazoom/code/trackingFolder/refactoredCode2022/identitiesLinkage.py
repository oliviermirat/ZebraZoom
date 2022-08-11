from scipy.optimize import linear_sum_assignment
import numpy as np
import math

def findOptimalIdCorrespondance(trackingHeadTailAllAnimalsList, wellNumber, i,  firstFrame):
  
  if i > firstFrame:
    
    costMatrix = np.zeros((len(trackingHeadTailAllAnimalsList[wellNumber]), len(trackingHeadTailAllAnimalsList[wellNumber])))
    
    for animalIdPrev in range(0, len(trackingHeadTailAllAnimalsList[wellNumber])):
      for animalIdCur in range(0, len(trackingHeadTailAllAnimalsList[wellNumber])):
        coordPrevX = trackingHeadTailAllAnimalsList[wellNumber][animalIdPrev, i-firstFrame-1][0][0]
        coordPrevY = trackingHeadTailAllAnimalsList[wellNumber][animalIdPrev, i-firstFrame-1][0][1]         
        coordCurX  = trackingHeadTailAllAnimalsList[wellNumber][animalIdCur,  i-firstFrame][0][0]
        coordCurY  = trackingHeadTailAllAnimalsList[wellNumber][animalIdCur,  i-firstFrame][0][1]
        # TO DO: add some very high cost for (0, 0) coordinates
        costMatrix[animalIdPrev, animalIdCur] = math.sqrt((coordCurX - coordPrevX)**2 + (coordCurY - coordPrevY)**2)
    
    row_ind, col_ind = linear_sum_assignment(costMatrix)
    
    return col_ind
    
  else:
    
    return np.array([k for k in range(0, len(trackingHeadTailAllAnimalsList[wellNumber]))])


def switchIdentities(correspondance, trackingHeadTailAllAnimalsList, trackingHeadingAllAnimalsList, wellNumber, i, firstFrame):
  
  trackingHeadTailAllAnimalsListWellNumberOriginal = trackingHeadTailAllAnimalsList[wellNumber][:, i-firstFrame].copy()
  trackingHeadingAllAnimalsListWellNumberOriginal  = trackingHeadingAllAnimalsList[wellNumber][:, i-firstFrame].copy()
  
  for previousId, newId in enumerate(correspondance):
    trackingHeadTailAllAnimalsList[wellNumber][previousId, i-firstFrame] = trackingHeadTailAllAnimalsListWellNumberOriginal[newId]

  for previousId, newId in enumerate(correspondance):
    trackingHeadingAllAnimalsList[wellNumber][previousId, i-firstFrame] = trackingHeadingAllAnimalsListWellNumberOriginal[newId]
  
  return [trackingHeadTailAllAnimalsList, trackingHeadingAllAnimalsList]

