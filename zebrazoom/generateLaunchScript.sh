# This script will output a shell script that will launch zebrazoom on all the videos present inside a specified folder.

# This script takes as parameters:
# 1 : path to the folder where all the videos you want to analyze are
# 2 : extension of the videos to analyze
# 3 : path to the configuration file

# Warning: you must put the full paths as parameters for this to work (c:/ etc...)

# For example, you could launch this: "./generateLaunchScript.sh c:/Users/mirat/Desktop/trackingVideos/ avi c:/Users/mirat/Desktop/configuration/config.json" in order to produce a script (called launch.sh) that would launch ZebraZoom on all the videos present inside the folder c:/Users/mirat/Desktop/trackingVideos/, with the configuration file c:/Users/mirat/Desktop/configuration/config.json

# The output script will be created in the folder $1

cd $1
rm launch.sh
for entry in *"$2"
do
  filename="${entry%.*}"
  echo $filename
  printf "python -m zebrazoom "$1" "$filename" "$2" "$3"\n"  >> launch.sh
done
