import numpy as np
import json
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
import json
import os

from PyQt5.QtWidgets import QFileDialog

import zebrazoom.code.util as util


def chooseVideoToTroubleshootSplitVideo(self, controller):

  # Choosing video to split
  self.videoToTroubleshootSplitVideo, _ =  QFileDialog.getOpenFileName(self.window, "Select video", os.path.expanduser("~"), "All files(*)")
  if not self.videoToTroubleshootSplitVideo:
    return

  def beginningAndEndChosen():
    # Choosing directory to save sub-video
    firstFrame = self.configFile["firstFrame"]
    lastFrame = self.configFile["lastFrame"]
    self.configFile = configFile
    directoryChosen = QFileDialog.getExistingDirectory(self.window, 'Choose in which folder you want to save the sub-video.')
    if not directoryChosen:
      return

    # Extracting sub-video

    cap = zzVideoReading.VideoCapture(self.videoToTroubleshootSplitVideo)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")

    frame_width  = int(cap.get(3))
    frame_height = int(cap.get(4))
    xmin = 0
    xmax = frame_width
    ymin = 0
    ymax = frame_height

    out = cv2.VideoWriter(os.path.join(directoryChosen, 'subvideo.avi'), cv2.VideoWriter_fourcc('M','J','P','G'), 10, (xmax-xmin,ymax-ymin))
    # out = cv2.VideoWriter(os.path.join(directoryChosen, 'subvideo.avi'), cv2.VideoWriter_fourcc('H','F','Y','U'), 10, (xmax-xmin,ymax-ymin))

    i = firstFrame
    maxx = lastFrame
    cap.set(1, i)
    while(cap.isOpened() and (i<maxx)):
      i = i + 1
      ret, frame = cap.read()
      if ret == True:
        frame2 = frame[ymin:ymax,xmin:xmax]
        if False:
          frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
          frame2 = cv2.cvtColor(frame2, cv2.COLOR_GRAY2BGR)
        out.write(frame2)
      else:
        break
    cap.release()

    self.show_frame("VideoToTroubleshootSplitVideo")

  configFile = self.configFile.copy()
  # User input of beginning and end of subvideo
  util.chooseBeginningPage(self, self.videoToTroubleshootSplitVideo, "Choose where the beginning of your sub-video should be", "Ok, I want the sub-video to start at this frame!",
                           lambda: util.chooseEndPage(self, self.videoToTroubleshootSplitVideo, "Choose where the sub-video should end.", "Ok, I want the sub-video to end at this frame!", beginningAndEndChosen),)
