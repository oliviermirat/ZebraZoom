import zebrazoom.dataAPI as dataAPI
import numpy as np

def testingWellAnimalBout(numWell, numAnimal, numBout):
  
  print("")
  print("numWell:", numWell, "; numAnimal:", numAnimal, "; numBout:", numBout)

  kinematicParametersAuto = dataAPI.getKinematicParametersPerBout(videoName, numWell, numAnimal, numBout)
  kinematicParametersManual = dataAPI.getNbOscAndTBFPerBoutFromManualClassification(videoName, numWell, numAnimal, numBout)

  print("Manual: Number of oscillations:", kinematicParametersManual[0], "; TBF (quotient):", kinematicParametersManual[1], "; Mean instantaneous TBF:", kinematicParametersManual[2])
  print("Automatic: Number of oscillations:", kinematicParametersAuto['Number of Oscillations'], "; Mean TBF (quotient):", kinematicParametersAuto['meanTBF'], "; Mean Instantenous TBF:", kinematicParametersAuto['Mean TBF (Hz)'], "; medianOfInstantaneousTBF:", kinematicParametersAuto['medianOfInstantaneousTBF'])
  
  print("Max absolute TBA (deg.):", kinematicParametersAuto['Max absolute TBA (deg.)'])
  print("Absolute Yaw (deg):", kinematicParametersAuto["Absolute Yaw (deg)"])
  # print("kinematicParametersAuto:", kinematicParametersAuto)
  print("Bout Duration (s):", kinematicParametersAuto["Bout Duration (s)"])
  print("Bout Distance (mm)", kinematicParametersAuto["Bout Distance (mm)"])
  
  dataAPI.plotManualVsAutomaticBendLocations(videoName, numWell, numAnimal, numBout)


videoName = "23.05.19.ao-07-f-1-2-long1"

outlierRemoval = False

dataAPI.plotKinematicParametersHist(videoName, "Max absolute TBA (deg.)", outlierRemoval)
dataAPI.plotKinematicParametersHist(videoName, "Absolute Yaw (deg)",      outlierRemoval)
boutDurations, max_bin_range = dataAPI.plotKinematicParametersHist(videoName, "Bout Duration (s)",       outlierRemoval)
dataAPI.plotKinematicParametersHist(videoName, "Bout Distance (mm)",      outlierRemoval)

boutDurationLimit = 0.5 # max_bin_range[1]
print("All bout durations added:", np.sum(boutDurations), "; Bout durations below " + str(boutDurationLimit) + " added:", np.sum([dur if dur > boutDurationLimit else 0 for dur in boutDurations]), "; percentage kept:", (np.sum([dur if dur > boutDurationLimit else 0 for dur in boutDurations]) / np.sum(boutDurations)) * 100)

# longer bout fish 0

numWell   = 0
numAnimal = 0
numBout   = 4
testingWellAnimalBout(numWell, numAnimal, numBout)

numWell   = 0
numAnimal = 0
numBout   = 20
testingWellAnimalBout(numWell, numAnimal, numBout)

numWell   = 0
numAnimal = 0
numBout   = 274
testingWellAnimalBout(numWell, numAnimal, numBout)

# longer bout fish 1

numWell   = 0
numAnimal = 1
numBout   = 195 # frames 72507 to 72596
testingWellAnimalBout(numWell, numAnimal, numBout)

numWell   = 0
numAnimal = 1
numBout   = 75
testingWellAnimalBout(numWell, numAnimal, numBout)

numWell   = 0
numAnimal = 1
numBout   = 111
testingWellAnimalBout(numWell, numAnimal, numBout)

# short bout fish 0

numWell   = 0
numAnimal = 0
numBout   = 76
testingWellAnimalBout(numWell, numAnimal, numBout)

numWell   = 0
numAnimal = 0
numBout   = 49
testingWellAnimalBout(numWell, numAnimal, numBout)

# strr = ''
# for key, value in f['configurationFileUsed'].attrs.items():
  # strr += f"{key}: {value}, "