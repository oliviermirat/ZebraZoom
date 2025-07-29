import numpy as np
import h5py


listOfFilenames = ["./ao.9dph.4000br.160hz.1000us.f10.1__2025_07_08-11_09_05.h5",
                   "./ao.9dph.4000br.160hz.1000us.f10.2__2025_07_08-11_09_06.h5",
                   "./ao.9dph.4000br.160hz.1000us.f11.8__2025_07_08-13_29_21.h5",
                   "./ao.9dph.4000br.160hz.1000us.f11.9__2025_07_08-13_25_24.h5"]

print("")
print("Successive bends is defined below as a frame detected as a bend for which the next frame is also a bend.")

for filename in listOfFilenames:
  
  f = h5py.File(filename, "r")

  videoDuration = (f.attrs['lastFrame'] - f.attrs['firstFrame']) / 160
  numberOfWells = len(f["wellPositions"])
  
  print("")
  print("For", filename, ":")

  for numWell in range(numberOfWells):
    
    numberOfAnimals = len(f["dataForWell0"])
    
    for numAnimal in range(numberOfAnimals):

      for numBout in range(0, int(f["dataForWell" + str(numWell) + "/dataForAnimal" + str(numAnimal) +"/listOfBouts"].attrs['numberOfBouts'])):
        
        Bend_Timing = f["dataForWell" + str(numWell) + "/dataForAnimal" + str(numAnimal) +"/listOfBouts/bout" + str(numBout) + "/Bend_Timing"][:]
        nbSuccessiveBends = np.sum(np.diff(Bend_Timing) == 1)
        frequency = nbSuccessiveBends / videoDuration
        print("For well", numWell, "and animal", numAnimal, ", the total number of successive bends is:", nbSuccessiveBends, "; or a frequency of:", frequency, "successive bends per second (during periods of times when bouts are occuring).")
        print("Total number of Bends detected:", len(Bend_Timing), "or a frequency of", len(Bend_Timing) / videoDuration, "bends per seconds (during periods of times when bouts are occuring).")
        print("Frequency of 'succesive bends' (relative to total number of bends detected):", int(nbSuccessiveBends / len(Bend_Timing) * 10000)/100, "%")
        