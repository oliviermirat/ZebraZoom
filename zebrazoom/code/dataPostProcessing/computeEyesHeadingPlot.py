import os
import matplotlib.pyplot as plt
import math
import pickle

def distBetweenAngles(angle1, angle2):
  diffAngle = angle2 - angle1
  if diffAngle < -math.pi:
    diffAngle = diffAngle + 2 * math.pi
  if diffAngle > math.pi:
    diffAngle = diffAngle - 2 * math.pi
  return diffAngle

def computeEyesHeadingPlot(superStruct, hyperparameters, videoName):
  
  outputPath = os.path.join(hyperparameters["outputFolder"], videoName)
  
  for wellId in range(0, len(superStruct["wellPoissMouv"])):
    for animalId in range(0, len(superStruct["wellPoissMouv"][wellId])):
      for boutId in range(0, len(superStruct["wellPoissMouv"][wellId][animalId])):
      
        leftEyeAngle   = superStruct["wellPoissMouv"][wellId][animalId][boutId]["leftEyeAngle"]
        rightEyeAngle  = superStruct["wellPoissMouv"][wellId][animalId][boutId]["rightEyeAngle"]
        heading        = superStruct["wellPoissMouv"][wellId][animalId][boutId]["Heading"]
        leftEyeArea    = superStruct["wellPoissMouv"][wellId][animalId][boutId]["leftEyeArea"]
        rightEyeArea   = superStruct["wellPoissMouv"][wellId][animalId][boutId]["rightEyeArea"]
        leftDiffAngle  = [distBetweenAngles(angle, heading[idx]) for idx, angle in enumerate(leftEyeAngle)]
        rightDiffAngle = [distBetweenAngles(angle, heading[idx]) for idx, angle in enumerate(rightEyeAngle)]
        
        if True:
          fig, tabAx = plt.subplots(2, 1, figsize=(22.9, 8.8))
          tabAx[0].plot([idx for idx, val in enumerate(leftDiffAngle)], leftDiffAngle)
          tabAx[0].set_title('Head direction angle - Left eye direction angle')
          tabAx[1].plot([idx for idx, val in enumerate(rightDiffAngle)], rightDiffAngle)
          tabAx[1].set_title('Head direction angle - Right eye direction angle')   
        else:
          fig, tabAx = plt.subplots(4, 1, figsize=(22.9, 8.8))
          tabAx[0].plot([idx for idx, val in enumerate(leftDiffAngle)], leftDiffAngle)
          tabAx[0].set_title('Head direction angle - Left eye direction angle')
          tabAx[1].plot([idx for idx, val in enumerate(leftEyeArea)], leftEyeArea)
          tabAx[1].set_title('Left eye area')
          tabAx[2].plot([idx for idx, val in enumerate(rightDiffAngle)], rightDiffAngle)
          tabAx[2].set_title('Head direction angle - Right eye direction angle')
          tabAx[3].plot([idx for idx, val in enumerate(rightEyeArea)], rightEyeArea)
          tabAx[3].set_title('Right eye area')
        
        plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_eyeDiffAngle_" + str(wellId) + '_' + str(animalId) + '_' + str(boutId) + '.png'))
        
        dataToSave = {"leftDiffAngle": leftDiffAngle, "rightDiffAngle": rightDiffAngle, "leftEyeArea": leftEyeArea, "rightEyeArea": rightEyeArea}
        with open(os.path.join(outputPath, hyperparameters["videoName"] + "_eyeDiffAnglePickleData_" + str(wellId) + '_' + str(animalId) + '_' + str(boutId) + '.pickle'), "wb") as f:
          pickle.dump(dataToSave, f)
        