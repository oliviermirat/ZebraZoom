cd $1
rm launch.sh
for entry in *"$2"
do
  filename="${entry%.*}"
  echo $filename
  printf "python ZebraZoom.py "$1" "$filename" "$2" "$3"\n"  >> ../launch.sh
done
cd ..
mv launch.sh ~/Desktop/launch.sh
