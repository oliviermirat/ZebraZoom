# TLDR: use this script to duplicate manually selected tail extremity and tail base prior to head embedded tail tracking.

# If you want to track multiple videos that are all in one folder you can manually select the tail extremity and tail base by clicking on "Run ZZ on multiple videos" and then "Manual first frame tail extremity" from the GUI home page.
# If you want to have the exact same manual tail extremity and tail base for all videos in your folder, you can do the manual selection of points for one and only one of the videos inside the folder (for example you can exit the GUI (with Ctrl+C) after having clicked on the tail extremity and base for only one of the video); and then use the script below.
# To use this script: place this script in the folder where all your videos are, then execute this script passing the name of the video for which you already did the manual selection as the first parameter of this script.

for entry in *.avi
do
  cp ${1}.avi.csv   ${entry}.csv
  cp ${1}.aviHP.csv ${entry}HP.csv
done
