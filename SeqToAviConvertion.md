<H1 CLASS="western" style="text-align:center;">Seq to avi convertion:</H1>

<p>
<b>Update (10/10/2021)</b>: it is now possible to use ZebraZoom with seq files directly either through the command line or through the GUI.

When using the GUI, just select the .seq file corresponding to the video you want to analyze.
When using the command line to launch the tracking, simply set the path and the video name to the .seq file of the video you want to analyze and the file extention to seq.

So the information below is now only relevant if for some reason you need to convert a seq video into an avi and not use it with ZebraZoom.
</p>

<br/><br/>

<p>
You can convert a video from the seq format (RDvision format) to avi, using the following command:

python -m zebrazoom convertSeqToAvi pathToVideo videoName codec lastFrame

while replacing:
- pathToVideo: by the path to the video that you want to convert
- videoName: by the name of the video that you want to convert (WITHOUT the file extension included in this name)
- codec: (OPTIONAL) by a 4 letter word such as 'MJPG' (if you want the video created to be of a smaller size, but with some potential small loss of information) or 'HFYU' (if you don't mind the video created to be very large, but with no loss of information). If you don't put anything for this parameter, it will be set automatically to 'HFYU'.
- lastFrame: (OPTIONAL) by the frame at which you want the convertion to stop (so the convertion will run from the frame 1 until the frame lastFrame). If you don't put anything for this parameter, the convertion will simply be done on the entire video.
</p>

<br/>

<p>
You can also convert a video from the seq format to avi and directly launch the tracking afterwards, using the following command:

python -m zebrazoom convertSeqToAviThenLaunchTracking pathToVideo videoName pathToConfigFile codec lastFrame

while replacing:
- pathToVideo: by the path to the video that you want to convert
- videoName: by the name of the video that you want to convert (WITHOUT the file extension included in this name)
- pathToConfigFile: by the the path to the configuration file you want to use for the tracking
- codec: (OPTIONAL) by a 4 letter word such as 'MJPG' (if you want the video created to be of a smaller size, but with some potential small loss of information) or 'HFYU' (if you don't mind the video created to be very large, but with no loss of information). If you don't put anything for this parameter, it will be set automatically to 'HFYU'.
- lastFrame: (OPTIONAL) by the frame at which you want the convertion to stop (so the convertion will run from the frame 1 until the frame lastFrame). If you don't put anything for this parameter, the convertion will simply be done on the entire video.
- (OPTIONAL): you can then also add a list of hyperparameter names followed by the values you want them to be at as you would when launching the tracking with the regular command line (to overwrite hyperparameter values set in the configuration file).
</p>
