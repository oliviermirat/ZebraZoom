import zebrazoom.dataAPI as dataAPI
import shutil
import os


# videoNameOri = "DSCF0046_2024_2024_12_24-10_55_43"
# videoNameOri = "DSCF0023_2024_2024_12_26-16_10_24"
# videoName = videoNameOri.replace("_2024_12", "_copy_2024_12")

videoNameOri = "DSCF0046_2024_2025_03_15-16_01_07"
videoName = videoNameOri.replace("_2025_03", "_copy_2025_03")

ZZoutputPath = os.path.join('zebrazoom', 'ZZoutput')

shutil.copyfile(os.path.join(ZZoutputPath, videoNameOri + ".h5"), os.path.join(ZZoutputPath, videoName + ".h5"))


max_distance_threshold = 20
max_dist_disapearedAnimal_step = 0.2
max_NbFramesAllowedToDisapeared = 80 #20
minimumTraceLength = 50 #10
removeNewDetectionsTooClose = 8
minDistTravel = 0 #5
minimumProbaDetectionForNewTrajectory = 0.1
removeStationaryPointMinDist = 0 #2
removeStationaryPointInterval = 0 # 14



nbAnimalsPerWell = 30

dataAPI.reassignMultipleAnimalsId(videoName, 1, nbAnimalsPerWell, 10, None, None, max_distance_threshold, max_dist_disapearedAnimal_step, max_NbFramesAllowedToDisapeared, minimumTraceLength, removeNewDetectionsTooClose, minDistTravel, minimumProbaDetectionForNewTrajectory, removeStationaryPointMinDist, removeStationaryPointInterval)

# dataAPI.reassignMultipleAnimalsId(videoName, 1, 200, 10, None, 10)
