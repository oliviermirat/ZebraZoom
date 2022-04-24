import json
import matplotlib.pyplot as plt
import cv2
import numpy as np
import math

import zebrazoom.code.util as util


readingSpeed = 70
zoom = 4

pathToVideos = '../zebrazoom/ZZoutput/'

listOfVideosTracked = ['example1', 'example2', 'example3']

boutForAllVideos = []

for videoName in listOfVideosTracked:
  
  with open(pathToVideos + videoName + '/results_' + videoName + '.txt') as video:
    
    supstruct = json.load(video)
    
    for numWell in range(0, len(supstruct['wellPoissMouv'])):
      
      for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
        
        for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
          
          # The "if" below is just for the example here so that we can go faster through all the videos
          # REMOVE the if below to go through ALL the bouts
          if numWell == 0 and numAnimal == 0 and numBout == 0:
          
            bout = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]
            print("Plotting information for the first bout made by the first animal in the first well of the video", videoName, "; Bout start:", bout["BoutStart"], "; Bout end:", bout["BoutEnd"])
            
            # Plotting the tail angle over time
            plt.plot(bout["TailAngle_smoothed"])
            plt.show()

            # Plotting tail shape over time
            height = 50
            width  = 60
            for numFrame in range(0, len(bout["TailX_HeadingReferential"])):
              TailX_HeadingReferentialNumFrame = bout["TailX_HeadingReferential"][numFrame]
              TailY_HeadingReferentialNumFrame = bout["TailY_HeadingReferential"][numFrame]
              blank_image = np.zeros((height, width, 3), np.uint8)
              for point in range(0, len(TailX_HeadingReferentialNumFrame)):
                cv2.circle(blank_image, (int(TailX_HeadingReferentialNumFrame[point]) + int(width/2), int(TailY_HeadingReferentialNumFrame[point])), 1, (255,255,255), -1)
              blank_image = cv2.resize(blank_image, (int(width * zoom), int(height * zoom)))
              util.showFrame(blank_image, title='bout', timeout=readingSpeed)
              
            # Plotting fish head and tail position over time
            height = 500
            width  = 500
            minX = 1000000
            minY = 1000000
            for numFrame in range(0, len(bout["TailX_HeadingReferential"])):
              minX = min(min(bout["TailX_VideoReferential"][numFrame]), minX)
              minY = min(min(bout["TailY_VideoReferential"][numFrame]), minY)
            minX = max(minX - 50, 0)
            minY = max(minY - 50, 0)
            for numFrame in range(0, len(bout["TailX_HeadingReferential"])):
              TailX_VideoReferentialNumFrame = bout["TailX_VideoReferential"][numFrame]
              TailY_VideoReferentialNumFrame = bout["TailY_VideoReferential"][numFrame]
              HeadX = bout["HeadX"][numFrame]
              HeadY = bout["HeadY"][numFrame]
              blank_image = np.zeros((height, width, 3), np.uint8)
              for point in range(0, len(TailX_HeadingReferentialNumFrame)):
                cv2.circle(blank_image, (int(TailX_VideoReferentialNumFrame[point] - minX), int(TailY_VideoReferentialNumFrame[point] - minY)), 3, (255,255,255), -1)
              heading = bout["Heading"][numFrame]
              cv2.line(blank_image, (int(HeadX - minX), int(HeadY - minY)), (int(HeadX - 20 * math.cos(heading) - minX), int(HeadY - 20 * math.sin(heading) - minY)), (0, 0, 255), 3) # Plotting heading
              cv2.circle(blank_image, (int(HeadX - minX), int(HeadY - minY)), 4, (0,255,0), -1)
              util.showFrame(blank_image, title='bout', timeout=readingSpeed)

            # Printing all available information for this bout
            print(bout.keys())


# List of available information for each bout:
# 'FishNumber' : Fish number in the well. If there's only one fish per well, this number will be 0.
# 'BoutStart'  : Frame at which the bout started.
# 'BoutEnd'    : Frame at which the bout ended.
# 'TailAngle_Raw' : Tail angle over time for the bout, without any smoothing.
# 'HeadX'         : Position on the x axis of the center of the head of the animal, for each frame.
# 'HeadY'         : Position on the y axis of the center of the head of the animal, for each frame.
# 'Heading_raw'   : Value of the main angle of the head of the animal, for each frame, without any smoothing.
# 'Heading'       : Value of the main angle of the head of the animal, for each frame, with smoothing.
# 'TailX_VideoReferential'   : Position on the x axis of each of the points along the tail of the animal, for each frame.
# 'TailY_VideoReferential'   : Position on the y axis of each of the points along the tail of the animal, for each frame.
# 'TailX_HeadingReferential' : Position on the x axis of each of the points along the tail of the animal, for each frame, when changing the referential such that the head of the animal is at the position (0, 0) and the y axis is aligned with the heading.
# 'TailY_HeadingReferential' : Position on the y axis of each of the points along the tail of the animal, for each frame, when changing the referential such that the head of the animal is at the position (0, 0) and the y axis is aligned with the heading.
# 'TailAngle_smoothed'  : Tail angle over time for the bout, with smoothing.
# 'Bend_TimingAbsolute' : List of frames at which the tail angle reached a local maximum or minimum.
# 'Bend_Timing'         : List of frames at which the tail angle reached a local maximum or minimum, with frame 0 being set at the beginning of the bout.
# 'Bend_Amplitude'      : List of amplitudes of the tail angles, for each of the local maximum or minimum reached by the tail angle.
