<H1 CLASS="western" style="text-align:center;">ZebraZoom Tracking Troubleshooting Tips</H1>

In order to run the tracking of ZebraZoom, you should start by creating a configuration file by clicking on "Prepare configuration file for tracking" in the main menu of ZebraZoom. Once your configuration file is ready, click on "Run ZebraZoom's Tracking on a video" and then before clicking on "Choose file", check the box "Run in debug mode": this will allow you to check if it looks like the tracking is working for your video with the configuration file you created or not. If it looks like it's not working, try following the tips below to improve the configuration file you initially created: you should iteratively try to adjust the configuration file with the tips below and try running the tracking with the "debug mode" until the tracking looks good enough.<br/>
Once the tracking seems to be working well in "debug mode", you can also try testing the tracking on a larger section of your video (but not all of the video, if it's a long video), by adding the parameters "firstFrame": frameNumberToStartTracking, "lastFrame": frameNumberToStopTheTracking, "backgroundExtractionForceUseAllVideoFrames": 1.<br/>
If none of this works, then click on "Troubleshoot" in the main menu of ZebraZoom and follow the instructions to send us a sub-video by email and we can try to help.<br/>

<a name="tableofcontent"/>

<H2 CLASS="western">Table of content:</H2>

<H3 CLASS="western">Center of mass tracking issues:</H3>

[Problems on borders](#problemOnBorders)<br/>
[Animals not detected](#animalsNotDetected)<br/>

<H3 CLASS="western">Freely swimming zebrafish tracking issues:</H3>

[Problems on borders](#problemOnBorders)<br/>
[Animals not detected](#animalsNotDetected)<br/>
[Zebrafish tail not tracked accurately](#zebrafishTailNotDetected)<br/>
[Bout detection issues](#boutDetectionIssues)<br/>
[Tail angle parameters calculation issues](#tailAngleParametersCalculationIssues)<br/>
[Eye Tracking](#eyeTracking)<br/>

<H3 CLASS="western">Head-embedded zebrafish tracking issues:</H3>

[Head embedded tracking issues](#headEmbedded)<br/>

<a name="problemOnBorders"/>
<H2 CLASS="western">Problems on the border of the well:</H2>
You can solve this problem by adding a <b>filter to the extracted background</b> of the video. To do this add in the configuration file:<br/>
"backgroundPreProcessMethod": ["erodeThenMin"], "backgroundPreProcessParameters": [[3]]<br/>
The value "3" above is just an example. You can put any value you want: higher values will lead to filtering for a higher number of pixels.<br/>

<a name="animalsNotDetected"/>
<H2 CLASS="western">Animals not detected:</H2>

First check that the values of "minArea" and "maxArea" are within the values of "minAreaBody" and "maxAreaBody". If they are not, set the value of "minArea" to the value of "minAreaBody" and the value of "maxArea" to the value of "maxAreaBody".<br/><br/>

When running the tracking in "debug mode" as adviced above, you will see a visualization window called "Tracked frame: Click on any key to proceed": on this visualization window, you should in theory see <b>non-white pixels on and only on pixels that are part of an animal</b>. If it looks like there are <b>too many non-white pixels</b>, then:<br/>
If "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax" is inside your configuration file and has a value different than zero, then you can try decreasing the value of that parameter.<br/>
If "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax" is not inside your configuration file then you can try decreasing the value of the parameter "minPixelDiffForBackExtract" instead.<br/>
If on the other hand it looks like there are <b>not enough non-white pixels</b>, then you can try increasing the values of those two parameters.<br/><br/>

If it looks like only the <b>small areas (made of non-white pixels)</b> representing an animal are the areas that are <b>not being detected</b>, you can try decreasing the values of the parameters "minArea" and "minAreaBody". If on the other hand it looks like it's only <b>large areas</b> (made of non-white pixels) representing an animal that are the areas that are <b>not being detected</b>, then you can try increasing the values of the parameters "maxArea" and "maxAreaBody".<br/><br/>

If it looks like <b>too many non-white pixels are found close to the edge of the wells</b> then add a filter on the background extracted as explained in the previous section.<br/><br/>

Finally, if some animals are sometimes not being detected at all no matter what, you can <b>add some post-processing of trajectories</b> to solve the problem. In order to do this, you will need to add the following parameters to your configuration file:<br/>
"postProcessMultipleTrajectories": 1, "postProcessMaxDistanceAuthorized" : 250, "postProcessMaxDisapearanceFrames" : 10<br/>
The values 250 and 10 are just examples here, you will need to further adjust those. "postProcessMaxDistanceAuthorized" is the maximum distance accepted (in pixels) above which it is considered that an animal was detected incorrectly (and thus the trajectory post-processing will be applied), and "postProcessMaxDisapearanceFrames" is the maximum number of frames for which the post-processing will consider that an animal can be incorrectly detected.<br/>
Additionnally, when adding this post-processing of trajectories, it's also usually better to also set the parameter "multipleHeadTrackingIterativelyRelaxAreaCriteria" to 0.<br/><br/>

NB: after extracting the background of the video, ZebraZoom extracts the foreground of a video (previously refered to as "non-white pixels") by finding the pixels of an image that have a value more than "minPixelDiffForBackExtract" different from the background. And when "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax" is set to a value different than 0, then ZebraZoom will iteratively adjust the value of "minPixelDiffForBackExtract" in order to make the number of non-white pixels found as close as possible to the value of "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax".<br/>

<a name="zebrafishTailNotDetected"/>

<H2 CLASS="western">Zebrafish tail not tracked accurately:</H2>
If "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax" is inside your configuration file and if it has a value different than zero, then:<br/>
if "recalculateForegroundImageBasedOnBodyArea" is set to 0, then you can try setting it to 1 instead. If after making that change the tail tip is being detected "too soon", you can try increasing the value of "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax". If on the other hand the tail tip is being detected at the right place but the tail tracking is sometimes innacurate, you can try decreasing the value of "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax".<br/><br/>

If "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax" is not inside your configuration file, then if the tail tip is detected "too soon", you could try increasing the value of the parameter "minPixelDiffForBackExtract". If on the other hand the tip of the tail is being detected at the right place but the tracking of the tail is sometimes incorrect, then you can try decreasing the value of this parameter "minPixelDiffForBackExtract".<br/>


<a name="boutDetectionIssues"/>
<H2 CLASS="western">Bout detection issues:</H2>
The best would probably be to go to the main menu of ZebraZoom and to try to further adjust the four parameters related to bout detection: <b>"thresForDetectMovementWithRawVideo", "minNbPixelForDetectMovementWithRawVideo", "frameGapComparision" and "halfDiameterRoiBoutDetect"</b>. Alternatively, you could also try adjusting those parameters manually: increasing "thresForDetectMovementWithRawVideo" or "minNbPixelForDetectMovementWithRawVideo" will decrease the length and the amount of bouts detected, while increasing "frameGapComparision" will increase the length and the amount of bouts detected.<br/>
Importantly, another important parameter is <b>"fillGapFrameNb"</b>, which controls the merging of bouts that are close to each other (in number of frames). Increasing the value of this parameter "fillGapFrameNb" will lead to more merging of bouts and decreasing it will lead to less merging.<br/>


<a name="tailAngleParametersCalculationIssues"/>
<H2 CLASS="western">Tail angle parameters calculation issues:</H2>
<a href="https://github.com/oliviermirat/ZebraZoom#hyperparametersTailAngleSmoothBoutsAndBendsDetect" target="_blank">Read this.</a>


<a name="eyeTracking"/>
<H2 CLASS="western">Eye Tracking:</H2>
It may be possible in some situations to track the eyes of the fish: for instance, this will only work if there are enough pixels per eye and if the eyes are much darker than the rest of the body of the zebrafish (swim bladder excluded): <a href="https://github.com/oliviermirat/ZebraZoom#eyesTracking" target="_blank">read this to learn more</a>.


<a name="headEmbedded"/>
<H2 CLASS="western">Head embedded tracking issues:</H2>
<a href="https://github.com/oliviermirat/ZebraZoom#extremeHeadEmbeddedTailTracking" target="_blank">Read this.</a>

