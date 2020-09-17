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
[Testing the installation and using ZebraZoom](#testanduse)<br/>
[Adjusting ZebraZoom's hyperparameters](#hyperparameters)<br/>
[Further analyzing ZebraZoom's output through the Graphical User Interface](#GUIanalysis)<br/>
[Further analyzing ZebraZoom's output with Python](#pythonanalysis)<br/>
[Troubleshooting ZebraZoom's tracking](#troubleshoot)<br/>
[Cite us](#citeus)<br/>

<a name="installation"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western"> Installation:</H2>

<H4 CLASS="western">General method:</H4>
Download and install <a href="https://www.anaconda.com/products/individual" target="_blank">Anaconda with Python 3.7</a> (scroll down to the bottom of that web page or click on the "Download button" on the top of that page). You may skip this step if you already have python 3.6 or higher installed on your computer.<br/>
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

<H4 CLASS="western">Very easy installation for Window 10:</H4>
If you are using Windows 10 (64 bits), there is an even easier method to install ZebraZoom!<br/>
Just <a href="https://drive.google.com/open?id=1XY9-qOHoGnaL_wIR4o0YMU3SQEPxniZF" target="_blank">download this file</a> and unzip it. Open the folder ZebraZoomWinExe, then double click on “doubleClickHereToStart”: the ZebraZoom graphical interface should start.<br/>
<b>Warning:</b> this installation method is a good way to easily test ZebraZoom. However, if you use the installation method described above instead, ZebraZoom's tracking will run faster.<br/>

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
Or, if you have installed ZebraZoom following the "Very easy installation for Window 10" method: open the folder ZebraZoomWinExe, then double click on “doubleClickHereToStart”.<br/>

<a name="testanduse"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Testing the installation and using ZebraZoom:</H2>
To be able to track animals in videos you need to create a configuration file for each “type” of video you want to track. A “type” of video is defined by light intensity, number and shape of wells, number of animals per well, number of pixels per animal, the type of animal in your video, etc...<br/><br/>
Start by testing that ZebraZoom is working on your machine. To do that, <a href="https://zebrazoom.org/testVideos.html" target="_blank">download the test videos</a> and try to run the tracking on those: in the GUI's main menu, click on “Run ZebraZoom on a video”, choose the video you want to track and then the configuration file which will have the same name as the video you want to track. Once the tracking is done, go back to the main menu and click on “Visualize ZebraZoom's output”, then on the video you just tracked. If the tracking worked well, you should be able to visualize the output produced by ZebraZoom (by clicking on “View video for well 0” for example).<br/><br/>
You can also watch the <a href="https://www.youtube.com/playlist?list=PLuWZiRK2HkeVo8zIPixdBj-hBk-cbsQZr" style="color:blue" target="_blank">tutorial videos on how to use ZebraZoom</a> for more guidance about how to create configuration files, launch ZebraZoom on videos and visualize the outputs.<br/>

<a name="hyperparameters"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Adjusting ZebraZoom's hyperparameters:</H2>
<H4 CLASS="western">Adjusting hyperparameters through the GUI:</H4>
In order to track videos other than the ones provided on ZebraZoom's website, you might need to create your own configuration files. In order to do that, you can click on “Prepare configuration file for tracking” and follow the steps described to create a configuration file adapted to the videos you want to track. Please note that this procedure isn't complete and may not work on all videos. If you don't manage to create a configuration file on your own, you can contact us at info@zebrazoom.org and we will try to make one for you.<br/>
Tip: once you've created a configuration file for some videos and launched the tracking on those videos using that configuration file, check the quality of the tracking and bouts extraction by clicking on “Visualize ZebraZoom's output”. If you are unsatisfied with the results, you can refine the configuration file you created by clicking on “Prepare configuration file for tracking” in the main menu and then by clicking on the box “Click here to start from a configuration file previously created (instead of from scratch)”: this will allow you to reload and refine the configuration file you already created. You can then save that refined configuration file and use it to re-tracked your videos.<br/>

<H4 CLASS="western">Further adjustments of tail angle smoothing and bouts and bends detection:</H4>
If you are tracking the tail of zebrafish larva, then you might need to further refine the parameters controlling the smoothing of the tail angle and the identification of bouts and bends. To do this, start by clicking on “Visualize ZebraZoom's output” and then on the name of the video you just tracked. Then look at some of the bouts and click on the button “Change Visualization” to compare the smoothed tail angle from which the bends are extracted with the raw un-smoothed tail angle. If the smoothing of the tail angle or the bouts and bends detection is not good enough, you can refine the configuration file to adjust the parameters controlling the smoothing and the bouts and bends detection. To do this, open your configuration file in a text editor (your configuration file should be in the folder ZebraZoom/configuration), and add/change the parameters listed below. You can then relaunch the tracking with that updated configuration file. When you relaunch the tracking, check the box “I ran the tracking already, I only want to redo the extraction of parameters.”.

<H5 CLASS="western">Post-processing of bouts initially detected: parameters below control the removal of “outlier bouts”</H5>

<font color="blue">detectBoutMinNbFrames</font> : default: 2:
minimum number of frames a bout must have to be detected

<font color="blue">detectBoutMinDist</font> : default: 4:
minimum distance traveled during the bout (between beginning and finish) for the bout to be detected

<font color="blue">detectBoutMinAngleDiff</font> : default: -1:
minimum variation of the angle (max(angle)-min(angle)) for the bout to be detected

<font color="blue">minNbPeaksForBoutDetect</font>: default: 2:
minimum required number of bends in a bout for the bout to be detected

<font color="blue">noChecksForBoutSelectionInExtractParams</font>: default: 0:
If set to 1, none of the checks described below will happen


<H5 CLASS="western">Parameters related to the smoothing of the tail angle</H5>

<font color="blue">tailAngleSmoothingFactor</font> : default: 0.001:
Smoothing factor applied on the tail angle. Higher values lead to more smoothing.

<font color="blue">tailAngleMedianFilter</font> : default: 3:
Window of the median filter applied to the tail angle (before smoothing).


<H5 CLASS="western">Parameters related to the detection of bends</H5>
<p>
These two first parameters control the initial detection of the bend through the “find_peaks” function of scipy (https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html).

<font color="blue">windowForLocalBendMinMaxFind</font> : default: 1:

<font color="blue">minProminenceForBendsDetect</font> : default: 0.01:

For time t, if the angle is a local minimum/maximum for the values between 
t-windowForLocalBendMinMaxFind and t+windowForLocalBendMinMaxFind, and if the “depth” of that maximum/minimum is at least minProminenceForBendsDetect, then a bend is detected at time t. If minProminenceForBendsDetect is equal to -1, then minProminenceForBendsDetect is set to minProminenceForBendsDetect = maxDiffPeakToPeak / 10,  maxDiffPeakToPeak being the difference between the maximum and the minimum values of the tail angle over the entire bout.


The parameters below control the post processing of the peaks previously found (they control the removal of “outlier bends”):

<font color="blue">minDiffBetweenSubsequentBendAmp</font> : default: 0.02:
if the bend “n” has a value X, then the bend “n+1” must have a value Y for which 
absoluteValue(X-Y) >  minDiffBetweenSubsequentBendAmp. If the bend “n+1” doesn't satisfy that condition, then the bend is not detected.

<font color="blue">minFirstBendValue</font> : default: -1: 
minimum value required for the first bend (so by default all bends are accepted)

<font color="blue">doubleCheckBendMinMaxStatus</font> : default: 1:
if doubleCheckBendMinMaxStatus is equal to 1, then only keeps bends for which:
bend(n-1) > bend(n) and bend(n) < bend(n+1)
bend(n-1) < bend(n) and bend(n) > bend(n+1)

<font color="blue">removeFirstSmallBend</font> : default: 0:
if removeFirstSmallBend is different than 0 (so not by default), then removes the first bend if:
abs(TailAngle_smoothed[firstBend]) < abs(TailAngle_smoothed[secondBend]) / hyperparameters["removeFirstSmallBend"]
</p>

<a name="GUIanalysis"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Further analyzing ZebraZoom's output through the Graphical User Interface:</H2>
Click on "Analyze ZebraZoom's outputs" in the main menu. Then you can choose to either compare different populations of animals with kinematic parameters or to cluster bouts of movements.

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

<a name="troubleshoot"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Troubleshooting tracking issues:</H2>
If you are having trouble tracking animals in a video, you can click on the button "Troubleshoot" in the main menu to create a smaller sub-video out of the video you are trying to track. Once this sub-video is created, you can send it to info@zebrazoom.org and we can try to help.

<a name="citeus"/>

<br/>[Back to table of content](#tableofcontent)<br/>
<H2 CLASS="western">Cite us:</H2>

<p>In all your publications that make use of ZebraZoom:</p>
<p>First and foremost, please acknowledge <a href="https://wyartlab.org/" style="color:blue" target="_blank">Claire Wyart's lab</a> that has been supporting the development of ZebraZoom for many years.</p>
<p>Please also cite the original <a href="https://www.frontiersin.org/articles/10.3389/fncir.2013.00107/full" style="color:blue" target="_blank">ZebraZoom paper</a>.</p>
<p>Please also consider mentioning our website <a href="https://zebrazoom.org/" style="color:blue" target="_blank">zebrazoom.org</a> and/or this github repository <a href="https://github.com/oliviermirat/ZebraZoom" style="color:blue" target="_blank">github.com/oliviermirat/ZebraZoom</a>.</p>
