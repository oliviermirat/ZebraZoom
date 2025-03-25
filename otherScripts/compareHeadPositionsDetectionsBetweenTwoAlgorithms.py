import zebrazoom.dataAPI as dataAPI
import numpy as np
import matplotlib.pyplot as plt

#####

video1 = "DSCF0053_CV_optimized_copy_2024_11_12-12_20_19"
video2 = "DSCF0053_DL_GauAnt_labels_copy_2024_11_12-13_32_40"

video1 = "DSCF0053_DL_GauAnt_labels_copy_2024_11_12-13_32_40"
video2 = "DSCF0053_CV_optimized_copy_2024_11_12-12_20_19"

video1 = "DSCF0053_CV_optimized_copy_2024_11_12-12_20_19"
video2 = "DSCF0053_DL_0.01"

#####

video1 = "DSCF0053_CV_optimized_2024_11_12-12_20_19"
video2 = "DSCF0053_DL_GauAnt_labels_2024_11_12-13_32_40"

# video1 = "DSCF0053_DL_GauAnt_labels_2024_11_12-13_32_40"
# video2 = "DSCF0053_CV_optimized_2024_11_12-12_20_19"

# video1 = "DSCF0053_CV_optimized_2024_11_12-12_20_19"
# video2 = "DSCF0053_DL_0.01"


##### Retrained with CCV but not in DL

video1 = "DSCF0053_CV_optimized_2024_11_12-12_20_19"
video2 = "DSCF0053_YOLOwithInCCVbutNotDL_2025_03_13-11_39_49"

# video1 = "DSCF0053_YOLOwithInCCVbutNotDL_2025_03_13-11_39_49"
# video2 = "DSCF0053_CV_optimized_2024_11_12-12_20_19"


#####


maxDistance = 100

#####

videoFPS  = 24
videoPixelSize = 0.01

dataAPI.setFPSandPixelSize(video1, videoFPS, videoPixelSize)
dataAPI.setFPSandPixelSize(video2, videoFPS, videoPixelSize)

numWell = 0
nbAnimals = 20

data1 = []
data2 = []

for numAnimal in range(nbAnimals):
  data1.append(dataAPI.getDataPerTimeInterval(video1, numWell, numAnimal, None, None, "HeadPos"))
  data2.append(dataAPI.getDataPerTimeInterval(video2, numWell, numAnimal, None, None, "HeadPos"))

coordinateNotFound = []
coordinateNotFound_frameNumber = []
coordinateFound = []
coordinateFound_frameNumber = []
for i in range(18000):
  for animal1 in range(nbAnimals):
    coordinates1 = data1[animal1][i]
    correpondingCoordinateFound = False
    for animal2 in range(nbAnimals):
      if not(correpondingCoordinateFound):
        coordinates2 = data2[animal2][i]
        if np.sqrt(np.sum((coordinates1 - coordinates2)**2)) < maxDistance:
          correpondingCoordinateFound = True
    if correpondingCoordinateFound:
      coordinateFound.append(coordinates1)
      coordinateFound_frameNumber.append(i)    
    else:
      coordinateNotFound.append(coordinates1)
      coordinateNotFound_frameNumber.append(i)

#####

def plotPoints(points):
  
  # Extract x and y coordinates
  x_coords = [point[0] for point in points]
  y_coords = [point[1] for point in points]

  # Plot the points with inverted y-axis
  plt.figure(figsize=(8, 6))
  plt.scatter(x_coords, y_coords, s=1, color='blue', label='Points')
  plt.gca().invert_yaxis()  # Invert the y-axis
  plt.title("Points with Inverted Y-Axis")
  plt.xlabel("X Axis")
  plt.ylabel("Y Axis (Inverted)")
  plt.legend()
  plt.grid(True)
  plt.show()

if False:
  plotPoints(coordinateNotFound)
  plotPoints(coordinateFound)

#####


def plotBothPoints(coordinateNotFound, coordinateFound):
    # Extract x and y coordinates for both datasets
    x_coords_not_found = [point[0] for point in coordinateNotFound]
    y_coords_not_found = [point[1] for point in coordinateNotFound]
    
    x_coords_found = [point[0] for point in coordinateFound]
    y_coords_found = [point[1] for point in coordinateFound]
    
    # Create a figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

    # Plot coordinateFound on the left
    axes[0].scatter(x_coords_found, y_coords_found, s=1, color='blue', label='Found Points')
    axes[0].set_title("coordinateFound")
    axes[0].set_xlabel("X Axis")
    axes[0].set_ylabel("Y Axis (Inverted)")
    axes[0].legend()
    axes[0].grid(True)

    # Plot coordinateNotFound on the right
    axes[1].scatter(x_coords_not_found, y_coords_not_found, s=1, color='red', label='Not Found Points')
    axes[1].set_title("coordinateNotFound")
    axes[1].set_xlabel("X Axis")
    axes[1].legend()
    axes[1].grid(True)
    
    plt.gca().invert_yaxis()


    # Adjust layout for better spacing
    plt.tight_layout()
    plt.show()


# Call the function with the data
plotBothPoints(coordinateNotFound, coordinateFound)



coordSearchList = [[884, 321], [578, 11], [473, 613], [580, 450], [1059,606], [537,719]]

coordSearchToRealMaxDist = 4

for coordSearch in coordSearchList:
  print("Searching for:", coordSearch)
  for ind, coord in enumerate(coordinateNotFound):
    if np.sqrt(np.sum((coord - np.array(coordSearch))**2)) <= coordSearchToRealMaxDist:
      print(ind, coord, coordinateNotFound_frameNumber[ind])
  print("")

print("Number unfound:", len(coordinateNotFound))