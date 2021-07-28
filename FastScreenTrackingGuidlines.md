<H1 CLASS="western" style="text-align:center;">Fast Screen Tracking Guidlines:</H1>


<H2 CLASS="western">Creating a configuration file for fast screen tracking:</H2>

<p>
To create a configuration file for this type of tracking, you can use the <a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/configuration/screenFastTrackingConfigFileTemplate.json" target="_blank">screenFastTrackingConfigFileTemplate</a> configuration file and modify the following parameters inside it according to the aspect of your video:

- "nbWells": number of wells that should be detected in your video
- "nbRowsOfWells": number of rows of wells in your video
- "nbWellsPerRows": number of well per row in your video
- "minPixelDiffForBackExtract": threshold for a pixel to be considered part of the foreground (see instructions below to set this parameter)
- "paramGaussianBlur": window used to apply a gaussian filter on each image of the video (see instructions below to set this parameter)
- "backgroundPreProcessParameters": set this parameter to [[num]] (where num must be an uneven number higher than 0) if there are some false foreground detections near the border; otherwise set to 0 (see instructions below to set this parameter)
- "postProcessRemoveLowProbabilityDetection" : set to 1 if you want frames for which there's a low probability that a fish was accurately detected to be ignored and for the tracking point on those frames to be replaced by tracking points calculated through a post-processing of trajectories; set to 0 otherwise
- "postProcessLowProbabilityDetectionThreshold" : threshold related to the previous parameter: the lower this threshold, the more initial fish detections will be ignored (and replaced by post-processed trajectories)
- "postProcessRemovePointsOnBordersMargin" : set to a number higher than 0 if you want tracking points detected near the borders to be replaced by post-processed trajectories
- "trackingPointSizeDisplay": size of the tracking point displayed on the validation video

In order to choose a value for the parameters "minPixelDiffForBackExtract", "paramGaussianBlur" and "backgroundPreProcessParameters", you can run the tracking of ZebraZoom with the configuration file <a href="https://github.com/oliviermirat/ZebraZoom/blob/master/zebrazoom/configuration/testThresholdsForFastScreen.json" target="_blank">testThresholdsForFastScreen</a> while adjusting the value of those three parameters inside that testThresholdsForFastScreen.json configuration file.

Running ZebraZoom on your video with that configuration file will allow you to visualize the impact of those different parameters on the image being processed by the tracking (a window will pop up showing those images when running ZebraZoom with that configuration file). The aim is for those images being visualized to have dark pixels on and only on the animals, with as little "false positive" dark pixels as possible. So the "backgroundPreProcessParameters" should be placed to a value different than 0 if false positive dark pixels are found near the borders of the wells and minPixelDiffForBackExtract should be placed to a higher value when pixels inside the well (but not the animal) are being found as dark pixels. Furthermore, the animal should have the aspect of a "guaussian" (we shouldn't be able to see the eyes, swim bladder, etc...), the parameter "paramGaussianBlur" can be adjusted for that.

Finally, after ZebraZoom has been ran once on a specific video with the configuration file testThresholdsForFastScreen, the parameter "reloadBackground" can be switched from 0 to 1 in order for the calculated background to be reloaded (and thus save time). The parameter "lastFrame" (and possibly also "firstFrame") can also be adjusted inside that configuration file depending on which section of the video you want to visualize. Finally, when running a video with this testThresholdsForFastScreen configuration you must also make sure that there isn't any output folder inside the ZZoutput folder corresponding to the video for which you want to adjust parameters.

</p>
