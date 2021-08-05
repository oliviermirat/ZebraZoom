<H1 CLASS="western" style="text-align:center;">ZebraZoom</H1>

Examples of videos tracked with ZebraZoom:<br/><br/>
<p align="center">
<img src="https://zebrazoom.org/videos/gif/output1.gif" height="250">
<img src="https://zebrazoom.org/videos/gif/output2.gif" height="250">
<img src="https://zebrazoom.org/videos/gif/output3.gif" height="250">
<img src="https://zebrazoom.org/videos/gif/output4.gif" height="250">
<img src="https://zebrazoom.org/videos/gif/ER.gif" height="250">
<img src="https://zebrazoom.org/videos/gif/mouse.gif" height="250">
</p>

<p>
ZebraZoom can be used to track the head and tail of freely swimming and of head-embedded larval and adult zebrafish. It can also be used to track the center of mass of other animal species, such as mice or drosophila. The software operates through an intuitive graphical user interface, making it very simple to use for people with no programming background.

View the <a href="https://www.youtube.com/playlist?list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr" target="_blank">tutorial videos</a> of how to use ZebraZoom:
- <a href="https://www.youtube.com/watch?v=uyhCoIlBwsM&list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr&index=2" target="_blank">Launching the tracking on a video </a>
- <a href="https://www.youtube.com/watch?v=6CJzV81Rdp8&list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr&index=2" target="_blank">Creating a configuration file to track a specific kind of video</a>
- <a href="https://www.youtube.com/watch?v=7GoCSNDqvak&list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr&index=4" target="_blank">Visualizing an output produced by ZebraZoom's tracking</a>
- <a href="https://www.youtube.com/watch?v=uqLhUKWHPE8&list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr&index=5" target="_blank">Comparing different populations of animals with kinematic parameters</a>

The Graphical user interface of ZebraZoom also offers options to launch the tracking on multiple videos all at once and to cluster bouts of movements into distinct behaviors with unsupervised machine learning. A troubleshooting option is also intergrated inside the graphical user interface.

</p>


For more information visit <a href="https://zebrazoom.org/" target="_blank">zebrazoom.org</a> or email us info@zebrazoom.org<br/>

<a name="tableofcontent"/>
<H2 CLASS="western">Table of content:</H2>

[Installation](#installation)<br/>
[Starting the GUI](#starting)<br/>
[Testing the installation and using ZebraZoom through the GUI](#testanduse)<br/>
[Using ZebraZoom through the command line](#commandlinezebrazoom)<br/>
[Checking the quality of the tracking](#trackingqualitycheck)<br/>

[Adjusting ZebraZoom's hyperparameters through the GUI](#hyperparameters)<br/>
[Adjusting ZebraZoom's hyperparameters: for testing/troubleshooting](#hyperparametersTesting)<br/>
[Adjusting ZebraZoom's hyperparameters: further adjustment of the tail angle smoothing, the bouts detection and bends detection](#hyperparametersTailAngleSmoothBoutsAndBendsDetect)<br/>
[Adjusting ZebraZoom's hyperparameters: head-embedded zebrafish tail tracking in difficult conditions](#extremeHeadEmbeddedTailTracking)<br/>
[Adjusting ZebraZoom's hyperparameters: image pre-processing](#hyperparametersImagePreprocessing)<br/>
[Adjusting ZebraZoom's hyperparameters: output folder and video](#hyperparametersOutputFolderAndVideo)<br/>
[Adjusting ZebraZoom's hyperparameters: other adjustments](#hyperparametersOtherAdjustments)<br/>
[Adjusting ZebraZoom's hyperparameters: eye tracking of zebrafish larvae](#eyesTracking)<br/>

[Further analyzing ZebraZoom's output through the Graphical User Interface](#GUIanalysis)<br/>
[Further analyzing ZebraZoom's output with Python](#pythonanalysis)<br/>

[Post-processing: Identifying moving and sleeping time periods for zebrafish](#movingAndSleepPeriodZebrafish)<br/>
[Post-processing: Calculating fish tail curvature](#curvature)<br/>
[Post-processing: Calculating tail angle heatmap](#tailAngleHeatMap)<br/>

[Troubleshooting ZebraZoom's tracking](#troubleshoot)<br/>
[Contributions and running ZebraZoom from the source code](#contributions)<br/>
[Cite us](#citeus)<br/>

<a name="installation"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western"> Installation:</H2>

<H4 CLASS="western">General method:</H4>
Download and install <a href="https://www.anaconda.com/products/individual" target="_blank">Anaconda</a> (scroll down to the bottom of that web page or click on the "Download button" on the top of that page). You may skip this step if you already have python 3.6 or higher installed on your computer.<br/>
Restart your computer.<br/>
Open the "Anaconda Prompt" or any other terminal.<br/>
Type:<br/>
<I>pip install zebrazoom</I><br/>
If you are on Mac, type:<br/>
<I>pip uninstall opencv-python</I><br/>
<I>pip install opencv-python-headless</I><br/>
That's it! ZebraZoom is now installed on your computer!<br/><br/>
If you want to upgrade to the latest release of ZebraZoom later on, you can type:<br/>
<I>pip install zebrazoom --upgrade</I><br/><br/>

To start ZebraZoom, you can now open the Anaconda Prompt or a terminal and type:<br/>
<I>python -m zebrazoom</I><br/>

<H4 CLASS="western">Further recommendations for installation with the general method:</H4>
If and only if you are going to use Anaconda extensively to install packages other than ZebraZoom, it can be a good idea to create an Anaconda Environment just for ZebraZoom.<br/>
To do this, first create an environment:<br/>
<I>conda create -n zebrazoom</I><br/>
Then activate the newly created environment:<br/>
<I>conda activate zebrazoom</I><br/>
Then install zebrazoom as explained in the previous section ("General method").<br/><br/>
To start ZebraZoom, you can now open the Anaconda Prompt or a terminal and type:<br/>
<I>conda activate zebrazoom</I><br/>
<I>python -m zebrazoom</I><br/><br/>
<a href="https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html" target="_blank">Read this for more information on Anaconda environments</a><br/>

<a name="starting"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Starting the GUI:</H2>
As written in the previous section, to launch ZebraZoom, simply open the Anaconda Prompt / terminal and type:<br/><br/>
<I>python -m zebrazoom</I><br/>
if you have installed ZebraZoom through the "general method".<br/><br/>
<I>conda activate zebrazoom</I><br/>
<I>python -m zebrazoom</I><br/>
if you have installed ZebraZoom following the "further recommendations".<br/><br/>

<a name="testanduse"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Testing the installation and using ZebraZoom through the GUI:</H2>
To be able to track animals in videos you need to create a configuration file for each “type” of video you want to track. A “type” of video is defined by light intensity, number and shape of wells, number of animals per well, number of pixels per animal, the type of animal in your video, etc...<br/><br/>
Start by testing that ZebraZoom is working on your machine. To do that, <a href="https://zebrazoom.org/testVideos.html" target="_blank">download the test videos</a> and try to run the tracking on those: in the GUI's main menu, click on “Run ZebraZoom on a video”, choose the video you want to track and then the configuration file which will have the same name as the video you want to track. Once the tracking is done, go back to the main menu and click on “Visualize ZebraZoom's output”, then on the video you just tracked. If the tracking worked well, you should be able to visualize the output produced by ZebraZoom (by clicking on “View video for well 0” for example).<br/><br/>
You can also watch the <a href="https://www.youtube.com/playlist?list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr" style="color:blue" target="_blank">tutorial videos on how to use ZebraZoom</a> for more guidance about how to create configuration files, launch ZebraZoom on videos and visualize the outputs.<br/>

<a name="validationvideoreadingtips"/>
<H4 CLASS="western">GUI validation video reading tips:</H4>
After clicking on "Visualize ZebraZoom's output" and then on the name of a video, you will have the ability to visualize validation videos by clicking on the buttons "View video for all wells together", "View video for well i", "View zoomed video for well i"or  "View bout's video". You will then be able to navigate that validation video with the following keys:<br/><br/>
- <b>"4" or "a" or "left arrow (on windows)"</b>: to go back 1 frame<br/>
- <b>"6" or "d" or "right arrow (on windows)"</b>: to go forward 1 frame<br/>
- <b>"s"</b>: to go back 20 frames<br/>
- <b>"w"</b>: to go forward 20 frames<br/>
- <b>"g"</b>: to go back 50 frames<br/>
- <b>"h"</b>: to go forward 50 frames<br/>
- <b>"f"</b>: to go back 100 frames<br/>
- <b>"j"</b>: to go forward 100 frames<br/><br/>
Then click on "q" to exit the viewing of the validation video.<br/>

<a name="flagingbouts"/>
<H4 CLASS="western">Adding flags to bouts:</H4>
After clicking on "Visualize ZebraZoom's output" and then on the name of a video, you will have the ability to flag bouts that you think should be ignored in your analysis (or conversely you can also decide to flag bouts of interest): this system can be useful when further <a href="#pythonanalysis">post-processing the outputs of ZebraZoom with Python</a>.<br/>
When you click on "Flag" it will add a field "flag" inside the json result structure (saved in the results_videoName.txt file) and it will set that flag to 1 (then clicking on "Unflag" will set that "flag" field to 0), and clicking on save SuperStruct will actually save those flags into the file (if you don't click on save superstruct before exiting, the flags won't be saved).


<a name="commandlinezebrazoom"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Using ZebraZoom through the command line:</H2>
You can also use ZebraZoom through the command line. To do this, you will have to open Anaconda Prompt or a terminal and type:<br/><br/>
<I>python -m zebrazoom pathToVideo nameOfVideo extensionOfVideo pathToConfigFile</I><br/><br/>
For example, you could type:<br/><br/>
<I>python -m zebrazoom c:\Users\mirat\Desktop\trackingVideos\ video1 avi c:\Users\mirat\Desktop\configuration\config.json</I><br/><br/>
Warning: depending on the operating system you're using, you may need to replace the "\\"s by "/"s.<br/><br/>
Using ZebraZoom through the command line can be particularly useful when you want to analyze a lot of videos located in different folders, or if you want to launch ZebraZoom on a server instead of on a desktop computer.<br/><br/>
If you need to generate a script that will launch ZebraZoom on multiple videos that are all present inside a same folder, using the same configuration file, you can take a look at <a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/generateLaunchScript.sh" target="_blank">this script</a>.<br/><br/>
Finally, it's possible to overwrite the parameters present in the configuration file with the following command:<br/><br/>
<I>python -m zebrazoom pathToVideo nameOfVideo extensionOfVideo pathToConfigFile nameOfParameter1 newParameter1Value nameOfParameter2 newParameter2Value nameOfParameter3 newParameter3Value</I><br/><br/>
(it's possible to add as many or as few parameters as needed)<br/><br/>

<br/><br/>


<a name="trackingqualitycheck"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Checking the quality of the tracking:</H2>

<H4 CLASS="western">Quality control for one video:</H4>
Once you've performed the tracking on a video, it is important to check the quality of this tracking. The easiest method to do so is to click on the button "Visualize ZebraZoom's output" in the main menu of the GUI, and then to click on the name of the video you analyzed. You can then use the graphical interface to go through a few bouts and to click on the button "View video for well i" for some of those bouts.<br/><br/>
For fishes, you should use the validation video to check that the tracking points are placed correctly on the head and along the tail of the animal (if you tracked the tail) and that the heading is correctly calculated. For animals other than fishes, you can simply check that the center of mass is correctly placed on each frame.<br/><br/>
If you set the configuration file to detect bouts of movements, you should also check that the bouts of movements are being detected at the right times: in this situation, the tracking points will be displayed when and only when a bout is occurring. Therefore, for this situation, you should check that the tracking points are displayed when and only when a bout of movement is occurring, be sure to check for both false negative as well as for false positive bout detections.<br/><br/>
If you are tracking the tail of fishes at a high enough frame rate (at ~100Hz minimum for zebrafish larvae, but a higher frequency is better) and if you are interested in calculating the parameters related to the tail maximum and minimum bends, then it will also be important to check that the minimum and maximum of bends are correctly detected. When the tail reaches a maximum or minimum bend, the extremity of the tail becomes red on the validation video: you can therefore check the correct detection this way. You can also look at the graph on the right side of the interface to check the detection of the bends (they are shown with orange vertical bars).<br/><br/>
Finally, if you set the configuration file in order to detect circular wells, you should also click on "Open ZebraZoom's output folder" in the main menu of the GUI, then on the name of the video you want to check, and then open the file repartition.jpg: this file should contain red circles on and only on the wells, so you can use this to check for correct detection of the wells.<br/><br/>
If you find the quality of the tracking to be insufficient, you can try to improve the configuration file that you're using and/or contact us to get some help.<br/>

<H4 CLASS="western">Quality control for a set of similar videos:</H4>
If you have a set of videos on which you want to perform a quality control, you should first focus on a few of the videos and check them thoroughly with the method described in the previous section. Once you're confident that the tracking is working well, you can quickly "scan" through all of the other videos (or through some of those videos, if your dataset is really large).


<a name="hyperparameters"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters through the GUI:</H2>
In order to track videos other than the ones provided on ZebraZoom's website, you might need to create your own configuration files. In order to do that, you can click on “Prepare configuration file for tracking” and follow the steps described to create a configuration file adapted to the videos you want to track. Please note that this procedure isn't complete and may not work on all videos. If you don't manage to create a configuration file on your own, you can contact us at info@zebrazoom.org and we will try to make one for you.<br/>
Tip: once you've created a configuration file for some videos and launched the tracking on those videos using that configuration file, check the quality of the tracking and bouts extraction by clicking on “Visualize ZebraZoom's output”. If you are unsatisfied with the results, you can refine the configuration file you created by clicking on “Prepare configuration file for tracking” in the main menu and then by clicking on the box “Click here to start from a configuration file previously created (instead of from scratch)”: this will allow you to reload and refine the configuration file you already created. You can then save that refined configuration file and use it to re-tracked your videos.<br/>


<a name="hyperparametersTesting"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters: for testing/troubleshooting:</H2>
When first trying out a configuration file, it can sometimes be a good idea to check the quality of the tracking on a smaller sub-video before launching the tracking on the entire video. For this, you can set the parameters "firstFrame" and "lastFrame" to, respectively, the frame where you want the tracking to start and to the frame where you want the tracking to end.<br/>
If you are using the parameters "firstFrame" and "lastFrame", it can then also often be useful to set the parameter "backgroundExtractionForceUseAllVideoFrames" to 1: this will allow the tracking to be performed from frame "firstFrame" to "lastFrame" but the extraction of the background however will be done using all frames in the video (the extraction of the background is often sub-optimal if done on too few frames).<br/>
If you are detecting wells in your video before the tracking, you can also set the parameter "onlyTrackThisOneWell" to the number of the well you want the tracking to be performed on. If this parameter is left to its default value of -1, then the tracking will be performed on all wells detected.<br/>
If you've already ran ZebraZoom on a video and you want to run that video again, you have the option of setting the parameters "reloadWellPositions" and "reloadBackground" to 1: as the names would suggest, this will reload the well positions and background in order to save time.<br/>
If you are using the <a href="#commandlinezebrazoom">command line</a> to launch the tracking, you can also set some of the "debugging parameters" (such as "debugExtractParams", "debugTracking", "debugTrackingPtExtreme", "debugExtractBack", "debugFindWells", "debugHeadingCalculation", "debugDetectMovWithRawVideo") to 1 to help you find where problems might be occuring.<br/>

<a name="hyperparametersTailAngleSmoothBoutsAndBendsDetect"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters: further adjustment of the tail angle smoothing, the bouts detection and bends detection:</H2>

If you are tracking the tail of zebrafish larva, you might need to further refine the configuration file parameters controlling the smoothing of the tail angle, the parameters controlling the detection of the bouts of movements, and the parameters controlling the detection of the local minimums and maximums of the tail angle (which we call the "bends").<br/><br/>

To check if adjusting those parameters is necessary, start by clicking on "Visualize ZebraZoom's output" and then on the name of the video you just tracked. Then look at some of the bouts and click on the button "Change Visualization" to compare the smoothed tail angle with the raw un-smoothed tail angle. Also pay close attention to where the bends are detected. You can also use the "View video" buttons to check if the bouts of movements are detected at the right times.<br/>
If the smoothing of the tail angle or the bouts or bends detection doesn't seem good enough, you can try to refine the configuration file you initially used: first open your configuration file in a text editor (you can access the folder where configuration files are stored by clicking on "Open configuration file folder" in the main menu), and then try to add and/or change some of the parameters listed below.<br/><br/>

Once your new configuration file is ready, relaunch the tracking with that updated configuration file.<br/>
If you relaunch the tracking from ZebraZoom's graphical interface, check the box "I ran the tracking already, I only want to redo the extraction of parameters" (this will reload saved tracked data instead of re-tracking the video, in order to speed up the analysis).<br/>
Optionally, you can also click the box "Don't (re)generate a validation video" to speed up the analysis even further: however be aware that in this case the validation video present in the output results folder won't necessarily correspond to the output data after your new analysis is done. Therefore, it can be a good idea to check that box if iteratively trying lots of configuration file options and then "un-checking it" for the final analysis.<br/>
If you are relaunching the tracking with the new configuration file (instead of from the GUI), then you can optionally set the following parameters to the specified values: "reloadWellPositions": 1, "reloadBackground": 1, "debugPauseBetweenTrackAndParamExtract": "justExtractParamFromPreviousTrackData" (this will have the same effect as checking the box "I ran the tracking already, I only want to redo the extraction of parameters" above) and you can also set the parameter "createValidationVideo" to 0 (which will have the same effect as checking the box "Don't (re)generate a validation video" above).<br/><br/>

There are a lot of parameters listed below which can be overwhelming. To begin adjusting these parameters, a good place to start could be to tweak the parameters "windowForLocalBendMinMaxFind", "tailAngleMedianFilter", and potentially also "tailAngleSmoothingFactor" (see below for more information about these parameters).<br/>
If some false positive bouts of movements are being detected, you can also set "noChecksForBoutSelectionInExtractParams" to 0 and further adjust the related parameters.<br/>
Importantly, please also note that the parameter "extractAdvanceZebraParameters" must be set to 1 in order for any of these calculations (removal of outlier bouts, tail angle smoothing, and bends detection) to occur.<br/><br/>

<H5 CLASS="western">Post-processing of the bouts of movements initially detected: the parameters below control the removal of "outlier bouts"</H5>

<font color="blue">noChecksForBoutSelectionInExtractParams</font>: default: 1:
If set to 1 (which is the default value), none of the checks described below will happen

<font color="blue">detectBoutMinNbFrames</font> : default: 2:
minimum number of frames a bout must have to be considered a "false positive" and thus removed

<font color="blue">detectBoutMinDist</font> : default: 4:
minimum distance traveled during the bout (between beginning and finish) for the bout to be considered a "false positive" and thus removed

<font color="blue">detectBoutMinAngleDiff</font> : default: -1:
minimum variation of the angle (max(angle)-min(angle)) for the bout to be considered a "false positive" and thus removed

<font color="blue">minNbPeaksForBoutDetect</font>: default: 2:
minimum required number of bends in a bout for the bout to be considered a "false positive" and thus removed
<br/><br/>

<H5 CLASS="western">Parameters related to the smoothing of the tail angle</H5>

<font color="blue">tailAngleSmoothingFactor</font> : default: 0.001:
Smoothing factor applied on the tail angle. Higher values lead to more smoothing.

<font color="blue">tailAngleMedianFilter</font> : default: 3:
Window of the median filter applied to the tail angle (before smoothing).
<br/><br/>

<H5 CLASS="western">Parameters related to the detection of bends (local minimums and maximums of the tail angle)</H5>
<p>
These two first parameters control the initial detection of the bends through the "find_peaks" function of scipy (https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html).

<font color="blue">windowForLocalBendMinMaxFind</font> : default: 1:

<font color="blue">minProminenceForBendsDetect</font> : default: 0.01:

If the value of the angle at frame n is a local minimum/maximum relative to all angles for the frames in the range n-windowForLocalBendMinMaxFind and n+windowForLocalBendMinMaxFind, and if the "depth" of that maximum/minimum is at least minProminenceForBendsDetect, then a bend is detected for frame n. If minProminenceForBendsDetect is equal to -1, then minProminenceForBendsDetect is set to minProminenceForBendsDetect = maxDiffPeakToPeak / 10, maxDiffPeakToPeak being the difference between the maximum and the minimum values of the tail angle over the entire bout.<br/>


The parameters below control the post processing of the peaks found with the method above: more precisely, they control the removal of "false-positive bends":

<font color="blue">minDiffBetweenSubsequentBendAmp</font> : default: 0.02:
if the bend "n" has a value X, then the bend "n+1" must have a value Y for which 
absoluteValue(X-Y) >  minDiffBetweenSubsequentBendAmp. If the bend "n+1" doesn't satisfy that condition, then the bend is considered a false-positive and thus removed.

<font color="blue">minFirstBendValue</font> : default: -1: 
minimum value required for the first bend in order to not be considered a false-positive (so by default all bends are accepted)

<font color="blue">doubleCheckBendMinMaxStatus</font> : default: 1:
if doubleCheckBendMinMaxStatus is equal to 1, then ZebraZoom only keeps bends for which:
(bend(n-1) > bend(n) and bend(n) < bend(n+1)) OR (bend(n-1) < bend(n) and bend(n) > bend(n+1))

<font color="blue">removeFirstSmallBend</font> : default: 0:
if removeFirstSmallBend is different than 0 (so not by default), ZebraZoom removes the first bend if:
abs(TailAngle_smoothed[firstBend]) < abs(TailAngle_smoothed[secondBend]) / hyperparameters["removeFirstSmallBend"]
<br/><br/>

<H4 CLASS="western">Detection of bout through tail angle variation instead of subsequent frames pixel differences:</H4>
The configuration files provided for the example files as well as the configuration files created through the GUI are set to make ZebraZoom detect bouts of movements by looking at the number of pixels that have a different intensity between subsequent frames of the video. It can sometimes be useful to instead detect the bouts by detecting variations in the tail angles. To do this, you must set the parameters in the configuration file as follow:<br/>
<font color="blue">"noBoutsDetection"</font>: 0,<br/>
<font color="blue">"thresForDetectMovementWithRawVideo"</font>: 0,<br/>
You must then choose the threshold for bout detection using the angle variation (in radians):<br/>
<font color="blue">"thresAngleBoutDetect"</font>: 0.1,<br/>
By default, the tail angle variation will be calculated on a period of 10 frames. To adjust this window you can adjust the following parameter:<br/>
<font color="blue">"windowForBoutDetectWithAngle":</font> 10,<br/>

</p>

<a name="extremeHeadEmbeddedTailTracking"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting hyperparameters for head-embedded zebrafish tail tracking in difficult conditions:</H2>
The contrast between the tail and the background can sometimes be low for head-embedded zebrafish. In this situation, during the configuration file creation procedure in the GUI, you should answer "Yes" to the question "Do you want to try to tweak tracking parameters further?" and then on "Adjust Tracking" (depending on the circumstances, checking the boxes "Choose the first frame for parameter adjustment" and "I want to adjust parameters over the entire video" can also be useful). You will then be able to go through the video by adjusting "Frame number" and/or with the keys "4" (backwards) and "6" (forward). The first parameter to try changing is often "headEmbededAutoSet_BackgroundExtractionOption". Then "headEmbededParamTailDescentPixThreshStopOverwrite", and then in some cases it can also be a good idea to try changing the other parameters as well.<br/><br/>
If after creating a custom configuration file with the method above you still don't get results that satisfy you, you can try manually adding:<br/>
<I>, "headEmbededRetrackIfWeirdInitialTracking" : 1</I><br/>
 in the configuration file that you previously created, and relaunch the tracking with that. Adding this parameter to the configuration file will make ZebraZoom "re-track" the tail with slightly different methods (which may lead to better results) for every frame for which the tracking seems incorrect. Please note however that at the time of this writing (28/12/2020), the way that ZebraZoom is checking if the tracking is incorrect or not is pretty basic: so if in your video the tail is moving with a lot of amplitude (or if "struggles" are present), then the procedure to check if the tracking is incorrect most likely won't work.<br/><br/>
Finally, you can also try manually adding and adjusting the parameters <I>"initialTailPortionMaxSegmentDiffAngleValue"</I> (default value is 1) and <I>"initialTailPortionMaxSegmentDiffAngleCutOffPos"</I> (default value 0.15) in the configuration file that you previously created. <I>"initialTailPortionMaxSegmentDiffAngleValue"</I> is the maximum difference "allowed" between two subsequently detected points along the tail of the animal near the base of the tail (starting from the base of the tail, going towards the tip of the tail); so decreasing the value of <I>"initialTailPortionMaxSegmentDiffAngleValue"</I> will force the tail tracking near the base of the tail to be more "straight".<br/>
<I>"initialTailPortionMaxSegmentDiffAngleCutOffPos"</I> represents the portion (from 0 to 1) that qualifies as "near the base of the tail". So 0.15 (the default value) means that the tail is considered as "near the base of the tail" from the base of the tail until 15% of the length of the tail.<br/><br/>
If after following the instructions above you still don't manage to create a configuration file that works well for your videos, please let us know by emailing us at info@zebrazoom.org (also please read the troubleshooting section below).


<a name="hyperparametersImagePreprocessing"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters: Image Pre-Processing:</H2>

<H3 CLASS="western">Image pre-processing before tracking:</H3>
It can sometimes be useful to preprocess the frames of the video before starting the tracking. The two parameters below can be used to this end:<br/>
<font color="blue">"imagePreProcessMethod" (default 0):</font> set it to a list of preprocessing methods you want to apply on all images before the tracking is performed on them. You can see the preprocessing methods available (and potentially add some more methods if necessary) in this file: <a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/code/preprocessImage.py" style="color:blue" target="_blank">preprocessImage.py</a>. For example, you could set this parameter to ["medianAndMinimum", "findNonGrayScalePixels"], in which case the "medianAndMinimum" filter will first be applied, followed by the "findNonGrayScalePixels" filter. By default (0), no preprocessing will be applied.<br/>
<font color="blue">"imagePreProcessParameters" (default []):</font> parameters of the previously specified preprocessing methods used. If you are using image preprocessing methods, you must set the parameters of the preprocessing methods here. For example, if you set "imagePreProcessMethod" to ["medianAndMinimum", "findNonGrayScalePixels"], you could then, for example, set "imagePreProcessParameters" to [[51], []].<br/><br/>

<H3 CLASS="western">Post-processing of the background extracted:</H3>
<font color="blue">"backgroundPreProcessMethod" (default 0):</font> same as "imagePreProcessMethod", except this will specify a list of post-processing methods to be applied on the background of the video, after it has been extracted.<br/>
<font color="blue">"backgroundPreProcessParameters" (default []):</font> same as "imagePreProcessParameters", except this specifies the values of the parameters specified in "backgroundPreProcessMethod".<br/><br/>


<a name="hyperparametersOutputFolderAndVideo"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters: output folder and video:</H2>

<H4 CLASS="western">Additional output folder</H2>
If you want to save the output result folder somewhere else than in the default output folder ZZoutput, you can set the parameter "additionalOutputFolder" to the path to a folder where your data will also be saved (in addition to being saved in the ZZoutput folder). Importantly, the path "additionalOutputFolder" must contain (at the end), the name of the final folder that will contain the files repartition.jpg, validationvideo.avi, etc... So for example, if you are analyzing the video Vid1 then you must set "additionalOutputFolder" to "~/Desktop/Vid1" in order for the results to be saved in the "Vid1" located on your Desktop.<br/>
If the folder "additionalOutputFolder" already exists, nothing will be saved in that folder, except if the parameter "additionalOutputFolderOverwriteIfAlreadyExist" is set to 1 in your configuration file (default value is 0).<br/>

<H4 CLASS="western">Improve contrast on validation video and invert black/white color (can be useful for head embedded fish)</H2>
If the contrast of your video is poor (for example if for head embedded fish the pixel intensity difference between the tail and the background is low), you can potentially set the parameter "outputValidationVideoContrastImprovement" to 1 in your configuration file: this will save a validation video with a better contrast and invert the black/white color in the video.<br/>
You can also adjust the amount of "contrast improvement" applied by adjusting the parameter "outputValidationVideoContrastImprovementQuartile": increasing this parameter will increase the amount of "contrast improvement" applied, while decreasing it will decrease the amount of "contrast improvement" applied.<br/>


<a name="hyperparametersOtherAdjustments"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters: other adjustments:</H2>

<H3 CLASS="western">Background extraction with only two frames of the video:</H3>
<font color="blue">"backgroundExtractionWithOnlyTwoFrames" (default 0):</font> set this parameter to 1 to perform the background subtraction with only two frames (the two frames will be chosen in order to maximise the amount of differences between the two frames). Setting this parameter to 1 can be useful to speed up the background extraction process and/or if for some reason using a lot of frames for the background extraction leads to problems.<br/><br/>

<H3 CLASS="western">Prevent issues when no movement is occuring (only works when wells are not detected at the moment):</H3>
Not having any movement occur in a video can sometimes lead to the tracking detecting tracking points at wrong locations. To solve this issue, you can adjust the two following parameters:<br/>
<font color="blue">"checkThatMovementOccurInVideo (default 0):</font> set to a value above 0 to avoid having the tracking being performed if it seems that no movement is occurring in the video. When launching ZebraZoom with this parameter set to a value above 0, ZebraZoom will print in the console:<br/>
<I>start get background<br/>
checkThatMovementOccurInVideo: max difference is: X<br/>
Background Extracted</I><br/>
When movement is occurring in the video, the value of X will be high; and when no movement is occurring, the value will be low. You should run ZebraZoom on several videos to determine a good threshold of this value of X between videos where movement is occurring and videos where no movement is occurring. Then, set <font color="blue">"checkThatMovementOccurInVideo</font> to that threshold to allow ZebraZoom to be able to differentiate between videos with movements and videos with no movements.<br/>
<font color="blue">"checkThatMovementOccurInVideoMedianFilterWindow" (default 11):</font> The previous method relies on a median filter that smooth images. You can adjust the window of that median filter with this parameter.<br/><br/>

<H3 CLASS="western">Freely swimming in "difficult conditions", mostly when low number of pixels per fish:</H3>
If you are trying to track freely swimming fish in "difficult conditions", especially if there's a low number of pixels per fish, you can try adjusting the following parameters:<br/>
<font color="blue">"headingCalculationMethod" (default "calculatedWithHead"):</font> set this parameter to "simplyFromPreviousCalculations" to keep the heading initially calculated during the initial stages of the calculation (calculated with the blob representing the head of the fish and the blob representing the body of the fish).<br/>
<font color="blue">"findContourPrecision" (default "CHAIN_APPROX_SIMPLE"):</font> set this parameter to "CHAIN_APPROX_NONE" in order to increase the accuracy of the tail calculation.<br/>
<font color="blue">"checkAllContourForTailExtremityDetect" (default 0):</font> set to 1 to avoid having the algorithm mismatch the head section of the contour with the tail section of the contour when looking for the tip of the tail<br/>
<font color="blue">"considerHighPointForTailExtremityDetect" (default 1):</font> set to 0 to avoid taking into consideration the "highest" point along the body of the fish as a tail extremity candidate point when looking for the tip of the tail.<br/>
<font color="blue">"erodeIter" (default 1):</font> set this parameter to 0, especially if there are many pixels not belonging to the fish set to black pixels after the thresholding.<br/><br/>

<H3 CLASS="western">Parameters related to the output validation video:</H3>
<font color="blue">"plotOnlyOneTailPointForVisu" (default 0):</font> if set to 1, it will only plot the tip of the tail on the validation video<br/>
<font color="blue">"trackingPointSizeDisplay" (default 1):</font> size of points displayed on the validation video<br/>
<font color="blue">"validationVideoPlotHeading" (default 1):</font> make sure this parameter is set to 1 if you want to see heading on your validation video<br/>
<font color="blue">"outputValidationVideoFps" (default -1):</font> fps of the output validation video (if value is strictly above 0). Otherwise, the fps of the output validation video will be the same as the fps of the input video.<br/><br/>


<H3 CLASS="western">Tracking for barely moving animals:</H3>
<p>
For freely moving animals (not for head embedded fish), if an animal on a video isn't moving or is barely moving then ZebraZoom won't be able to extract the background of the video and thus the tracking won't work.

However, if you want to track a video for which the animal is barely moving and for which the background is fairly uniform and on which the border of wells can't be seen (or if you launch the tracking on a ROI where the borders of the wells can't be seen), then you can create a configuration file using a special technique:

After clicking on "Prepare configuration file for tracking" from the main menu of the GUI, check the box "Click here to start from a configuration file previously created (instead of from scratch)." then after clicking "Select the video you want to create a configuration file for", choose the configuration file barelyMovingFish.json provided in the configuration file folder, and then the video you want to create a configuration file for. For freely moving fish, it is usually advised to then choose the "Recommended method: Automatic Parameters Setting". Creating a configuration file using this technique will make ZebraZoom set the background of the video to a uniform image equal to the median of the initially extracted background which should allow ZebraZoom to perform an accurate tracking in most cases.

</p>


<H3 CLASS="western">Other parameters:</H3>
<font color="blue">"fillGapFrameNb" (default 5):</font> try to decrease this if the bouts detected are too long, try increasing if the bouts detected are too short or if they are "cut" into several different pieces.<br/>


<a name="eyesTracking"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters: Eye tracking of zebrafish larvae:</H2>
This will only work if there are enough pixels per eye and if the eyes are much darker than the rest of the body of the zebrafish (swim bladder excluded). To make the eye tracking work, set the following parameters to the appropriate values:<br/>
<font color="blue">"eyeTracking" (default 0):</font> Set this parameter to 1 for the eye tracking to be performed.<br/>
<font color="blue">"headCenterToMidEyesPointDistance" (default 10):</font> approximate distance (in pixels) between the center of the head (automatically detected by ZebraZoom) and the mid-point between the center of the two eyes.<br/>
<font color="blue">"eyeBinaryThreshold" (default 50):</font> threshold value (between 0 and 255) to differentiate the eyes (and the swim bladder) from the rest of the body.<br/>
<font color="blue">"midEyesPointToEyeCenterMaxDistance" (default 10):</font> maximum accepted distance (in pixels) between the mid-eye point and the center of an eye<br/>
<font color="blue">"eyeHeadingSearchAreaHalfDiameter" (default 40):</font> half diameter (in pixels) of the sub-image on which the heading is calculated for an eye.<br/>
<font color="blue">"headingLineValidationPlotLength" (default 10):</font> length (in pixels) of the heading line plotted on the image during the eye tracking debugging (when the parameter "debugEyeTracking" is set to 1).<br/><br/>

It's also important to note that you can set the parameter "debugEyeTracking" and "debugEyeTrackingAdvanced" to 1 to troubleshoot this eye tracking.

<br/><br/>



<a name="GUIanalysis"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Further analyzing ZebraZoom's output through the Graphical User Interface:</H2>
Click on "Analyze ZebraZoom's outputs" in the main menu. Then you can choose to either compare different populations of animals with kinematic parameters or to cluster bouts of movements.<br/><br/>

<H3 CLASS="western">Units of output parameters for comparaison of populations with kinematic parameters:</H3>
When the results are first saved after the tracking (in the file results_videoName.txt in the subfolder ZZoutput/videoName) the units are simply in pixels (for spatial resolution) and frames (for time resolution). However, when using the option "Analyze ZebraZoom's outputs" from the main menu of the GUI, you will need to choose an "organization excel file". This "organization excel file" contains a column named "fq" and another column named "pixelsize". In the column "pixelsize" you must put the size of the pixels in your video and you can choose the unit for this value of pixel size (it could be in μm, mm, cm, m, etc...): this choice will then be reflected in the units of speed and distance travel calculated: for example if you choose mm for the pixel size, then the distance traveled calculated will also be in mm. Similarly, in the column "fq" you must put the frequency of acquisition of the video: if you put this unit in Hz (1/second) then the time unit for the duration and speed calculated will be in seconds; and if you decided to put in this column a frequency of acquisition in 1/minute, then the time unit for duration and speed will also be in minutes.

<H3 CLASS="western">Launching the kinematic parameters analysis through the command line instead of the GUI:</H3>
<p>
To launch the same kinematic parameter analysis from the command line, you can use the following command:

python -m zebrazoom dataPostProcessing kinematicParametersAnalysis pathToExcelFile frameStepForDistanceCalculation minimumNumberOfBendsPerBout keepSpeedDistDurWhenLowNbBends thresholdInDegreesBetweenSfsAndTurns

while putting the parameters: 

- pathToExcelFile: to the path to the excel file describing your experiment (the combination of several videos and what they correspond to)

- frameStepForDistanceCalculation: to calculate the distance travelled for each bout, in order to avoid the noise caused by subsequent close-by (x, y) coordinates of the center of the head of the animal, the (x, y) coordinates to calculate the total distance are not taken for every frame of the bout, but rather for every 'frameStepForDistanceCalculation' frame in the bout. When accessed from the GUI, this parameter is fixed to 4, which is a parameter that works well in many situations. When launching the analysis from the command line, this parameter can be further fine tuned. In the future, it will also be possible to fine tune this parameter from the GUI.

- minimumNumberOfBendsPerBout: the minimum number of bends that a bout must have in order for the parameters number of oscillations, tail beat frequency and maximum bend amplitude to be calculated for that bout and included in the analysis (this is for fish only)

- keepSpeedDistDurWhenLowNbBends: when a bout is removed from the analysis because it has a low amount of bends, then the parameters distance, duration and speed are kept in the analysis if keepSpeedDistDurWhenLowNbBends is set to 0, and they are discarded otherwise. If the distance, duration and speed parameters are kept then the parameters number of oscillations, tail beat frequency and maximum bend amplitude are set to nan for those bouts.

- thresholdInDegreesBetweenSfsAndTurns: threshold (unit in degrees) to separate a sfs from a turn (this is also for fish only)

Please note that the parameters minimumNumberOfBendsPerBout, keepSpeedDistDurWhenLowNbBends and thresholdInDegreesBetweenSfsAndTurns are all optional parameters. Therefore, if you don't put anything for:

- minimumNumberOfBendsPerBout and keepSpeedDistDurWhenLowNbBends then the parameters number of oscillations, tail beat frequency and max tail amplitude (all these parameters or for fish only) won't be calculated

- thresholdInDegreesBetweenSfsAndTurns then no information about the amount of turns and sfs based on a threshold over the max tail amplitude will be calculated



</p>

<a name="pythonanalysis"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Further analyzing ZebraZoom's output with Python:</H2>

A result folder will be created for each video you launch ZebraZoom on inside the ZZoutput folder.

If you have launch ZebraZoom on a video named “video”, you can load the results in Python with the following code:<br/>
<I>import json<br/>
with open('ZZoutput/video/results_video.txt') as f:<br/>
&nbsp;&nbsp;supstruct = json.load(f)</I>

Then, you can see the data for the well numWell, the animal numAnimal, and the bout numBout using the following command:
<I>supstruct['wellPoissMouv'][numWell][numAnimal][numBout]</I>


For example, if you want to look at the data for the first bout of the "animal 1" in the third well, you can type:<br/>
<I>supstruct['wellPoissMouv'][2][0][0]</I>

You can then, for example, plot the tail angle with the following command:

<I>import matplotlib.pyplot as plt</I><br/>
<I>plt.plot(supstruct['wellPoissMouv'][2][0][0]["TailAngle_smoothed"])</I><br/>
<I>plt.show()</I><br/>

The full list of parameters available for each bout is:<br/>
<I>'FishNumber'</I> : Fish number in the well. If there's only one fish per well, this number will be 0.<br/>
<I>'BoutStart'</I>  : Frame at which the bout started.<br/>
<I>'BoutEnd'</I>    : Frame at which the bout ended.<br/>
<I>'TailAngle_Raw'</I> : Tail angle over time for the bout, without any smoothing.<br/>
<I>'HeadX'</I>         : Position on the x axis of the center of the head of the animal, for each frame.<br/>
<I>'HeadY'</I>         : Position on the y axis of the center of the head of the animal, for each frame.<br/>
<I>'Heading_raw'</I>   : Value of the main angle of the head of the animal, for each frame, without any smoothing.<br/>
<I>'Heading'</I>       : Value of the main angle of the head of the animal, for each frame, with smoothing.<br/>
<I>'TailX_VideoReferential'</I>   : Position on the x axis of each of the points along the tail of the animal, for each frame.<br/>
<I>'TailY_VideoReferential'</I>   : Position on the y axis of each of the points along the tail of the animal, for each frame.<br/>
<I>'TailX_HeadingReferential'</I> : Position on the x axis of each of the points along the tail of the animal, for each frame, when changing the referential such that the head of the animal is at the position (0, 0) and the y axis is aligned with the heading.<br/>
<I>'TailY_HeadingReferential'</I> : Position on the y axis of each of the points along the tail of the animal, for each frame, when changing the referential such that the head of the animal is at the position (0, 0) and the y axis is aligned with the heading.<br/>
<I>'TailAngle_smoothed'</I>  : Tail angle over time for the bout, with smoothing.<br/>
<I>'Bend_TimingAbsolute'</I> : List of frames at which the tail angle reached a local maximum or minimum.<br/>
<I>'Bend_Timing'</I>         : List of frames at which the tail angle reached a local maximum or minimum, with frame 0 being set at the beginning of the bout.<br/>
<I>'Bend_Amplitude'</I>      : List of amplitudes of the tail angles, for each of the local maximum or minimum reached by the tail angle.<br/>

Here's also an <a href="./readAndAnalyzeZZoutputWithPython/readBouts.py" style="color:blue" target="_blank">example script</a> used to process the outputs of ZebraZoom.



<a name="movingAndSleepPeriodZebrafish"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Post-processing: Identifying moving and sleeping time periods for zebrafish</H2>

<H4 CLASS="western">Identifying moving and sleeping times of zebrafish:</H4>

The sleep and moving time periods can be calculated with the command:<br/>

python -m zebrazoom dataPostProcessing sleepVsMoving videoName speedThresholdForMoving notMovingNumberOfFramesThresholdForSleep<br/>

while replacing:<br/>
- videoName : by the name of the video for which you want to calculate the sleep and moving time periods.<br/>
If you want to do this analysis on several videos and also create a summary excel file about all the videos combined, you can also set this variable to a list of video names separated by commas. For example if you want to launch this analysis on three videos called video1, video2 and video3, you can set this variable to:<br/>
video1,video2,video3<br/>
Please note that there shouldn't be any spaces inside this variable: no spaces before or after the commas and no spaces inside the video names.<br/>
- speedThresholdForMoving : by a number representing the speed threshold between moving and non-moving time periods<br/>
- notMovingNumberOfFramesThresholdForSleep : by a number representing the 'number of frames not moving' threshold between sleep and non-sleep time periods<br/>

Optionally, some additional parameters can be added to the 'python -m zebrazoom dataPostProcessing etc...' line above, in the following order:<br/>
- specifiedStartTime : time at which the experiment started, you must specify this parameter in the format Hours:Minutes:Seconds (for example this could be 00:03:18 for 3 hours and 18 minutes, or it could be 15:00:07 for 15 hours and 7 seconds, etc...). You can also put this parameter at 0 for the time 00:00:00
- distanceTravelledRollingMedianFilter : window of a rolling median filter applied on the distance travelled (before the speed is calculated). If this parameter is not specified (by default), no rolling median filter is applied.<br/>
- videoPixelSize : pixelSize of the video, if this parameter is not specified it will be set to the 'videoPixelSize' parameter set in the configuration file used to launch the tracking (and if also unspecified in the configuration file, it will be set to the value 1)<br/>
- videoFPS : fps of the video, if this parameter is not specified it will be set to the 'videoFPS' parameter set in the configuration file used to launch the tracking (and if also unspecified in the configuration file, it will be set to the value 1)<br/>

Launching this analysis with the command line 'python -m zebrazoom dataPostProcessing etc...' will generate an excel file containing all the information about instantaneous speed, moving and sleep time periods for each frame and each well of the video. The excel file is saved inside the result folder of each video (result folders are all stored inside the 'ZZoutput' folder) (and the 'ZZoutput' folder can be accessed by clicking on 'Open ZebraZoom's output folder: Access raw data' from the main menu of ZebraZoom's GUI (Graphical User Interface) (which can be opened with 'python -m zebrazoom').<br/>

<H4 CLASS="western">Moving and sleeping times validation through visualization:</H4>

In order to validate the moving and sleeping time periods calculated, it is then possible to visualize moving and sleeping time periods with the following commands:<br/>

python -m zebrazoom visualizeMovingAndSleepingTime movingTime videoName<br/>
(while replacing 'videoName' by the name of the video for which you want to validate results)<br/>
This command will show the coordinates of fish when and only when the previous script has found that the fish is moving.<br/>

python -m zebrazoom visualizeMovingAndSleepingTime sleepingTime videoName<br/>
(while replacing 'videoName' by the name of the video for which you want to validate results)<br/>
This command will show the coordinates of fish when and only when the previous script has found that the fish is sleeping.<br/>

Both commands above are loading results directly from the excel files previously generated in order to validate the time periods calculated in the most straightforward manner possible.<br/>
This validation through visualization will only work if the parameter 'copyOriginalVideoToOutputFolderForValidation' was set to 1 in the configuration file used to launch the tracking.<br/>
For both commands above, you can easily go through the video using the following tips: https://zebrazoom.org/validationVideoReading.html<br/><br/>

<H4 CLASS="western">Identifying first sleeping time after specified time:</H4>

This can be done with the command:<br/>
python -m zebrazoom dataPostProcessing firstSleepingTimeAfterSpecifiedTime videoName specifiedTime wellNumber <br/>
Where:<br/>
videoName must be replaced either by the name of a video or by a list of video names separated by commas as explained in the paragraph "Identifying moving and sleeping times of zebrafish" above (if you want to launch this script on the excel file created by combining several videos) (please note that there shouldn't be any spaces anywhere in this variable).<br/>
specifiedTime must be replaced by a time in the format Hours:Minutes:Seconds (for example this could be 00:03:18 for 3 hours and 18 minutes, or it could be 15:00:07 for 15 hours and 7 seconds, etc...).<br/>
wellNumber must be the number of the well on which to launch this analysis (please note that well numbers start at 0 (not at 1)). If you set wellNumber to -1, the analysis will be launch on all wells.<br/>

<H4 CLASS="western">Calculating the number of sleeping and moving frames in-between two specified times:</H4>

This can be done with the command:<br/>
python -m zebrazoom dataPostProcessing numberOfSleepingAndMovingTimesInTimeRange videoName specifiedStartTime specifiedEndTime wellNumber <br/>
Where:<br/>
videoName must be replaced either by the name of a video or by a list of video names separated by commas as explained in the paragraph "Identifying moving and sleeping times of zebrafish" above (if you want to launch this script on the excel file created by combining several videos) (please note that there shouldn't be any spaces anywhere in this variable).<br/>
specifiedStartTime and specifiedEndTime must be replaced by a time in the format Hours:Minutes:Seconds (for example this could be 00:03:18 for 3 hours and 18 minutes, or it could be 15:00:07 for 15 hours and 7 seconds, etc...).<br/>
wellNumber must be the number of the well on which to launch this analysis (please note that well numbers start at 0 (not at 1)). If you set wellNumber to -1, the analysis will be launch on all wells.<br/>



<a name="curvature"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Post-processing: Calculating fish tail curvature:</H2>
To make ZebraZoom calculate the curvature of every bout detected, you can set the parameter <I>"perBoutOutput"</I> to 1 (the default value is 0).<br/>
This will create in each of the output folders a subfolder called "perBoutOutput" that will contain for each bout detected: a plot of the tail angle, the curvature plot, a pickle file containing the curvature data (see <a href="https://github.com/oliviermirat/ZebraZoom/blob/master/readAndAnalyzeZZoutputWithPython/loadCurvature.py" style="color:blue" target="_blank">here an example</a> of how to load pickled data), and a short video of the bout with the fish position being adjusted in order for the head of the fish to be in the middle top of the video and the main axis of the tail to be aligned with the y axis.<br/>
The curvature is being calculated using the method described in this <a href="https://en.wikipedia.org/wiki/Curvature#In_terms_of_a_general_parametrization" style="color:blue" target="_blank">Wikipedia page</a> (see the section "In terms of a general parametrization") in this <a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/code/perBoutOutput.py" style="color:blue" target="_blank">section of the ZebraZoom code</a>.<br/><br/>

You can also adjust the following parameters inside the configuration file:<br/>
- <I>"perBoutOutputVideoStartStopFrameMargin"</I> (default value is 0): this will create a video of the bout starting perBoutOutputVideoStartStopFrameMargin frames before the beginning of the bout and ending perBoutOutputVideoStartStopFrameMargin frames after the bout.<br/>
- <I>"perBoutOutputYaxis"</I>: you can specify the range of the y axis of the tail angle plot with this parameter. For example choosing the value [-100, 100] will create a tail angle plot axis going from -100 to 100. When no value is set for this parameter (by default), the range of the y axis will be automatically chosen by matplotlib.<br/>
- <I>"nbTailPoints"</I>: number of points tracked along the tail (default value is 10)<br/>
- <I>"curvatureMedianFilterSmoothingWindow"</I>: 2d median filter applied on the curvature plot (the default value, 0, will lead to no median filter being applied)<br/>
- <I>"smoothTailHeadEmbeded"</I>: Warning: you should most likely keep this parameter to its default value, -1. Indeed, choosing another value (higher than 0) will lead to a smoothing of the points along the tail of the animal: from experience, we have observed that such smoothing can lead to inaccurate curvature values.<br/>
- <I>"nbPointsToIgnoreAtCurvatureBeginning"</I> and <I>"nbPointsToIgnoreAtCurvatureEnd"</I> represents the number of points to NOT plot / ignore when plotting the curvature (starting from respectively the rostral and caudal ends of the tail) (default values for both of these parameters is 0). The parameter <I>"nbPointsToIgnoreAtCurvatureBeginning"</I> can be useful when the tracking is too noisy close to the base of the tail for "good" curvature values to be calculated. <I>"nbPointsToIgnoreAtCurvatureEnd"</I> could be useful in similar circumstances.<br/><br/>

As an example, you can calculate the curvature of the two example videos provided with ZebraZoom (<a href="https://drive.google.com/file/d/1ERVQZvTzBD69jUEjBOTA9BvH4gOdwC7N/view" style="color:blue" target="_blank">headEmbeddedZebrafishLarva.avi</a> and <a href="https://drive.google.com/file/d/1y00yli9XbcJlzFSbJgnVAM9yDvCWNCb2/view" style="color:blue" target="_blank">4wellsZebrafishLarvaeEscapeResponses.avi</a>) with the two configuration files initially provided, just by adding a few parameters to these initial configuration files:<br/>
- For headEmbeddedZebrafishLarva.avi you can use the configuration provided (<a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/configuration/headEmbeddedZebrafishLarva.json" style="color:blue" target="_blank">headEmbeddedZebrafishLarva.json</a>) by adding the two parameters <I>"perBoutOutput": 1</I> and <I>"nbTailPoints": 20</I> to it.<br/>
- For 4wellsZebrafishLarvaeEscapeResponses.avi, you can use the configuration file provided (<a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/configuration/4wellsZebrafishLarvaeEscapeResponses.json" style="color:blue" target="_blank">4wellsZebrafishLarvaeEscapeResponses.json</a>) by adding the two parameters <I>"perBoutOutput": 1</I> and <I>"nbPointsToIgnoreAtCurvatureBeginning": 1</I><br/>

(if needed, you can launch ZebraZoom <a href="#commandlinezebrazoom">through the command line</a> in order to easily overwrite/add those two parameters to the configuration file initially provided)


<a name="tailAngleHeatMap"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Post-processing: Calculating tail angle heatmap:</H2>
You can make ZebraZoom compute tail angle heatmaps for each bout detected by adding the parameter:<br/>
"tailAnglesHeatMap" : 1<br/>
in your configuration file.<br/><br/>
This calculation can be based on 2 to 9 points along the tail of the animal. By default, 8 points will be taken into account, but this parameter can be adjusted by changing the value of "tailAnglesHeatMapNbPointsToTakeIntoAccount" in the configuration file (default is 8).<br/>

<a name="troubleshoot"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Troubleshooting tracking issues:</H2>
If you are having trouble tracking animals in a video, you can click on the button "Troubleshoot" in the main menu to create a smaller sub-video out of the video you are trying to track. Once this sub-video is created, you can send it to info@zebrazoom.org and we can try to help.

<a name="contributions"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Contributions and running ZebraZoom from the source code:</H2>

We welcome contributions, feel free to submit pull requests!<br/><br/>
In order to contribute, you will need to download this repository on your computer. To run ZebraZoom, you must then navigate to the root folder of this repository inside a terminal and type "python -m zebrazoom" as shown in the previous sections <a href="#commandlinezebrazoom" style="color:blue">"Using ZebraZoom through the command line"</a> and <a href="#starting" style="color:blue">"Starting the GUI"</a> above (except that you must make sure to be in the root folder of this repository).<br/>

<a name="citeus"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Cite us:</H2>

<p>In all your publications that make use of ZebraZoom:</p>
<p>First and foremost, please acknowledge <a href="https://wyartlab.org/" style="color:blue" target="_blank">Claire Wyart's lab</a> that has been supporting the development of ZebraZoom for many years.</p>
<p>Please also cite the original <a href="https://www.frontiersin.org/articles/10.3389/fncir.2013.00107/full" style="color:blue" target="_blank">ZebraZoom paper</a>.</p>
<p>Please also mention this github repository <a href="https://github.com/oliviermirat/ZebraZoom" style="color:blue" target="_blank">github.com/oliviermirat/ZebraZoom</a> and/or our website <a href="https://zebrazoom.org/" style="color:blue" target="_blank">zebrazoom.org</a>.</p>
