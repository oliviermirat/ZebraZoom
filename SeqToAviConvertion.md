<H1 CLASS="western" style="text-align:center;">Seq to avi convertion:</H1>

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
