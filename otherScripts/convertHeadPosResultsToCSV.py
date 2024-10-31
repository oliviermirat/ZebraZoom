import zebrazoom.dataAPI as dataAPI
import numpy as np

videoName = "CF_1_4_ala3R_Exp5_copy_2024_09_30-19_10_50"
startTimeInSeconds = None
endTimeInSeconds   = None

nbWells = 4

for numWell in range(nbWells):
  
  numAnimal = 0
  
  data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "HeadPos")

  np.savetxt("headPosData" + str(numWell) + ".csv", data, delimiter=",", fmt="%d")
