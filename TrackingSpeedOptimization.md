<H1 CLASS="western" style="text-align:center;">ZebraZoom Tracking Speed Optimization for the "Track heads and tails of freely swimming fish" option</H1>

At the moment, these speed optimizations are only available with the "Track heads and tails of freely swimming fish" option (this is an option available in the GUI configuration file creation system).

<H3 CLASS="western">First speed optimization technique: trackOnlyOnROI_halfDiameter parameter:</H3>
In order to speed up the tracking, you can run the tracking procedure only on a region of interest (ROI) centered around the previous position of the fish. Set the parameter trackOnlyOnROI_halfDiameter in the configuration file to a value different than 0 in order for this to work. You should set the parameter trackOnlyOnROI_halfDiameter to the half diameter of the ROI you want the tracking to be performed on. The tracking procedure is set up in a way that if it "thinks" that there is a high probability that the fish is not inside the ROI for a frame, then the whole image will be used to find the next tracking position (not just the ROI).

<H3 CLASS="western">Second speed optimization technique: detectMovementWithRawVideoInsideTracking parameter:</H3>
By default, the detection of movement with the raw video is performed after the tracking. By setting the parameter "detectMovementWithRawVideoInsideTracking" to 1 inside the configuration file, this detection of movement will be performed at the same time as the tracking procedure is performed which should speed up the entire procedure.

<H3 CLASS="western">Third speed optimization technique: manual setting of parameters:</H3>
With the "Track heads and tails of freely swimming fish" option, there are 3 different tracking / background extraction options. From the "Optimize a previously created configuration file" -> "Optimize fish freely swimming tail tracking configuration file parameters", you can improve the tracking speed by choosing the "method 1". From the "Prepare initial configuration file for tracking" -> "Track heads and tails of freely swimming fish" you can choose the option "Alternative method: Manual Parameters Setting" (which is the same thing as "method 1"). However, keep in mind that choosing this "method 1" might decrease the quality of the tracking, especially if the quality of the video is sub-optimal.
