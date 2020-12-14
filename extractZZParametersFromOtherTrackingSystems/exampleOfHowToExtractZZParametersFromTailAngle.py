import zebrazoom
import csv
  
data      = open("tailAngle1.csv", "r")
tailAngle = [float(l) for l in data.read().split(',')]

print("tailAngle:", tailAngle)

videoName = "tailAngle1"

zebrazoom.extractZZParametersFromTailAngle(videoName, tailAngle)
