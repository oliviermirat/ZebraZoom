import zebrazoom.dataAPI as dataAPI
import numpy as np
import pickle

videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/23.05.19.ao-07-f-1-2-long1_2024_01_09-17_37_45.h5"
numWell   = 0

res = []

numAnimal = 0
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 69378, 69646))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 69655, 69754))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 70148, 70196))

numAnimal = 1
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 800, 846))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 897, 939))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 974, 1020))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 1045, 1153))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 1172, 1235))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 1325, 1425))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 1610, 1683))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 3758, 3803))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 4529, 4557))
res.append(dataAPI.getKinematicParametersPerInterval(videoName, numWell, numAnimal, 4566, 4637))

all_TBFQuotient = []
all_TBFInsta    = []
all_TBFQuotient2 = []
all_TBFInsta2    = []
for r in res:
  print(r)
  print("")
  all_TBFQuotient.append(r["meanTBF"])
  all_TBFInsta.append(r["Mean TBF (Hz)"])
  all_TBFQuotient2.append(r["TBF_quotient"])
  all_TBFInsta2.append(r["TBF_instantaneous"])

print("all_TBFQuotient:", all_TBFQuotient)
print("all_TBFInsta:", all_TBFInsta)
print("Mean/Median of TBF quotient:", np.mean(all_TBFQuotient), np.median(all_TBFQuotient))
print("Mean/Median of TBF instantaneous:", np.mean(all_TBFInsta), np.median(all_TBFInsta))

print("all_TBFQuotient:", all_TBFQuotient2)
print("all_TBFInsta:", all_TBFInsta2)
print("Mean/Median of TBF quotient:", np.mean(all_TBFQuotient2), np.median(all_TBFQuotient2))
print("Mean/Median of TBF instantaneous:", np.mean(all_TBFInsta2), np.median(all_TBFInsta2))

# Save array as pickle file
with open("goodTracking.pkl", 'wb') as f:
    pickle.dump(res, f)
