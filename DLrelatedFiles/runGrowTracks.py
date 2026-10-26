import os
import shutil
import zebrazoom.dataAPI as dataAPI

original = r"C:\Users\mirat\Desktop\openZZ\ZebraZoom\zebrazoom\ZZoutput\DSCF0062_2026_10_25-13_54_33.h5"

# Work on a copy, so the original result stays untouched (the function overwrites HeadPos in place).
# The label goes BEFORE the timestamp, because ZebraZoom expects names ending with "_YYYY_MM_DD-HH_MM_SS".
folder, name = os.path.split(original)
videoName, timestamp = name[:-23], name[-23:]
copy = os.path.join(folder, videoName + "-growTracks" + timestamp)
shutil.copyfile(original, copy)

# dataAPI.growTracksFromConfidentDetections(copy, 0, 200, maxDisplacement=5)
dataAPI.growTracksFromConfidentDetections(copy, 0, 200, maxDisplacement=3, exclusionRadius=10)  # without stacked duplicate tracks

print("Result written to", copy)
