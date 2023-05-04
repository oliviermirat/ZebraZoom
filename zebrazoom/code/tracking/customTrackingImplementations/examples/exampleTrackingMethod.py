import zebrazoom.code.tracking
import math
import cv2

class ExampleTrackingMethod(zebrazoom.code.tracking.BaseTrackingMethod):
  
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._wellPositions = wellPositions
    self._hyperparameters = hyperparameters

  def run(self):
    
    ### Step 1 (out of 2): Tracking:
    
    # Getting video reader
    cap = cv2.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")
    
    # Simple background extraction with first and last frame of the video
    ret, self._background = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
    ret, frame = cap.read()
    self._background = cv2.max(frame, self._background)
    self._background = cv2.cvtColor(self._background, cv2.COLOR_BGR2GRAY)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    # Initializing variables
    ret = True
    trackingDataPerWell = {}
    for wellNumber in range(0, len(self._wellPositions)):
      trackingDataPerWell[wellNumber] = []
    
    # Going through each frame of the video
    while (ret):
      ret, frame = cap.read()
      if ret:
      
        # Subtracting background of image
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        putToWhite = ( frame.astype('int32') >= (self._background.astype('int32') - self._hyperparameters["minPixelDiffForBackExtract"]) )
        frame[putToWhite] = 255
      
        # Going through each well/arena/tank and applying tracking method on it
        for wellNumber in range(0, len(self._wellPositions)):
          
          # Retrieving well/tank/arena coordinates and selecting ROI
          wellXtop = self._wellPositions[wellNumber]['topLeftX']
          wellYtop = self._wellPositions[wellNumber]['topLeftY']
          lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
          lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
          frameROI = frame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X].copy()
          
          # Applying gaussian filter to find the location of the animal
          paramGaussianBlur = 35
          frameROI = cv2.GaussianBlur(frameROI, (paramGaussianBlur, paramGaussianBlur), 0)
          (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
          
          # Storing track data for current well and current frame
          trackingDataPerWell[wellNumber].append(headPosition)
    
    
    ### Step 2 (out of 2): Extracting bout of movements:
    
    outputData = {} # Each element of this object will correspond to the tracking data of a particular well/tank/arena
    
    for wellNumber in range(0, len(self._wellPositions)):
      
      outputDataForWell = []
        
      if self._hyperparameters["detectBouts"]: # See below ("else") for no bout detection scenario
        
        nbFramesStepToAvoidNoise = 10
        minNbFramesForBoutDetect = 10
        
        # Finding frames with an instantaneous distance over a predifined threshold
        boutOccuring = [math.sqrt((trackingDataPerWell[wellNumber][i+nbFramesStepToAvoidNoise][0] - trackingDataPerWell[wellNumber][i][0])**2 + (trackingDataPerWell[wellNumber][i+nbFramesStepToAvoidNoise][1] - trackingDataPerWell[wellNumber][i][1])**2) > self._hyperparameters["minimumInstantaneousDistanceForBoutDetect"] for i in range(0, len(trackingDataPerWell[wellNumber])-nbFramesStepToAvoidNoise)]
        
        # Detecting bouts by finding long enough sequence of frames with high enough instantaneous distance
        boutCurrentlyOccuring = False
        boutFrameNumberStart  = -1
        for frameNumber, boutIsOccuring in enumerate(boutOccuring):
          if boutIsOccuring:
            if not(boutCurrentlyOccuring):
              boutFrameNumberStart = frameNumber
            boutCurrentlyOccuring = True
          else:
            if boutCurrentlyOccuring:
              boutCurrentlyOccuring = False
              if frameNumber - boutFrameNumberStart > minNbFramesForBoutDetect:
                # Saving information for each bout of movement detected
                boutOfMovement = {}
                boutOfMovement["AnimalNumber"]  = 0
                boutOfMovement["BoutStart"]     = boutFrameNumberStart
                boutOfMovement["BoutEnd"]       = frameNumber
                boutOfMovement["HeadX"]         = [trackingDataPerWell[wellNumber][i][0] for i in range(boutFrameNumberStart, frameNumber)]
                boutOfMovement["HeadY"]         = [trackingDataPerWell[wellNumber][i][1] for i in range(boutFrameNumberStart, frameNumber)]
                # Other keys can be added to "boutOfMovement", such as: Heading, TailAngle_Raw, TailX_VideoReferential, TailY_VideoReferential (see documentation)
                # You may also add: leftEyeX, leftEyeY, leftEyeAngle, leftEyeArea, rightEyeX, rightEyeY, rightEyeAngle, rightEyeArea: please contact us if you would like to track the eyes
                outputDataForWell.append(boutOfMovement)
      
      else: # No bout detction in this case
        boutOfMovement = {}
        boutOfMovement["AnimalNumber"]  = 0
        boutOfMovement["BoutStart"]     = 0
        boutOfMovement["BoutEnd"]       = len(trackingDataPerWell[wellNumber])
        boutOfMovement["HeadX"]         = [trackingDataPerWell[wellNumber][i][0] for i in range(0, len(trackingDataPerWell[wellNumber]))]
        boutOfMovement["HeadY"]         = [trackingDataPerWell[wellNumber][i][1] for i in range(0, len(trackingDataPerWell[wellNumber]))]
        # Other keys can be added to "boutOfMovement", such as: Heading, TailAngle_Raw, TailX_VideoReferential, TailY_VideoReferential (see documentation)
        # You may also add: leftEyeX, leftEyeY, leftEyeAngle, leftEyeArea, rightEyeX, rightEyeY, rightEyeAngle, rightEyeArea: please contact us if you would like to track the eyes
        outputDataForWell.append(boutOfMovement)        
      
      # Saving all tracked bouts of movements for current frame
      outputData[wellNumber] = outputDataForWell
    
    return outputData


zebrazoom.code.tracking.register_tracking_method('examples.exampleTrackingMethod', ExampleTrackingMethod)
