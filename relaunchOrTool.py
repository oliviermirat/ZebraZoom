import os
import shutil
import zebrazoom.dataAPI as dataAPI

# Your existing results file (from the tracking run you already did):
original = r"C:\Users\mirat\Desktop\openZZ\ZebraZoom\zebrazoom\ZZoutput\DSCF0062_ortool0.01_2026_10_20-11_37_17.h5"

# Work on a copy, so your first result stays untouched for comparison.
# The label goes BEFORE the timestamp, because ZebraZoom expects names ending with "_YYYY_MM_DD-HH_MM_SS".
folder, name = os.path.split(original)
videoName, timestamp = name[:-23], name[-23:]          # "DSCF0062" and "_2026_10_20-10_39_00.h5"
copy = os.path.join(folder, videoName + "-alternative" + timestamp)
shutil.copyfile(original, copy)

# alternative = {
  # "OrTools_output_p_confirm": 0.3,     # suggestion 1
  # "OrTools_level1_w_score": 1.0,       # suggestion 2
  # "OrTools_level1_p_entry": 0.25,      # suggestion 3
  # "OrTools_level1_entry_cost": 4,      # suggestion 4
  # "OrTools_level1_exit_cost": 4,
  # "OrTools_level2_entry_cost": 3,
  # "OrTools_level2_exit_cost": 3,
# }

alternative = {
  "OrTools_level1_p_neutral": 0.2,
}

dataAPI.trackWithOrToolsLevel1Only(copy, 0, 200, alternative)
# dataAPI.trackWithOrTools(copy, 0, 200, alternative)   # well 0, nbAnimalsPerWell = 200