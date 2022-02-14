import numpy as np
import json
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
import cvui
import json
import os

from PyQt6.QtWidgets import QFileDialog


def chooseVideoToTroubleshootSplitVideo(self, controller):

  # Choosing video to split
  self.videoToTroubleshootSplitVideo, _ =  QFileDialog.getOpenFileName(self.window, "Select video", os.path.expanduser("~"), "All files(*)")

  # User input of beginning and end of subvideo

  firstFrame = 1
  lastFrame  = 1000

  cap = zzVideoReading.VideoCapture(self.videoToTroubleshootSplitVideo)
  max_l = int(cap.get(7)) - 2

  cap.set(1, 1)
  ret, frame = cap.read()
  WINDOW_NAME = "Choose where the beginning of your sub-video should be."
  WINDOW_NAME_CTRL = "Control"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  cvui.init(WINDOW_NAME_CTRL)
  cv2.moveWindow(WINDOW_NAME_CTRL, 0, 300)
  value = [1]
  curValue = value[0]
  buttonclicked = False
  widgetX = 40
  widgetY = 20
  widgetL = 300
  while not(buttonclicked):
      value[0] = int(value[0])
      if curValue != value[0]:
        cap.set(1, value[0])
        frameOld = frame
        ret, frame = cap.read()
        if not(ret):
          frame = frameOld
        curValue = value[0]
      frameCtrl = np.full((200, 750), 100).astype('uint8')
      frameCtrl[widgetY:widgetY+60, widgetX:widgetX+widgetL] = 0
      cvui.text(frameCtrl, widgetX, widgetY, 'Frame')
      cvui.trackbar(frameCtrl, widgetX, widgetY+10, widgetL, value, 0, max_l)
      cvui.counter(frameCtrl, widgetX, widgetY+60, value)
      buttonclicked = cvui.button(frameCtrl, widgetX, widgetY+90, "Ok, I want the sub-video to start at this frame!")

      cvui.text(frameCtrl, widgetX, widgetY+130, 'Keys: 4 or a: move backwards; 6 or d: move forward')
      cvui.text(frameCtrl, widgetX, widgetY+160, 'Keys: g or f: fast backwards; h or j: fast forward')
      cvui.imshow(WINDOW_NAME, frame)
      cvui.imshow(WINDOW_NAME_CTRL, frameCtrl)
      r = cv2.waitKey(20)
      if (r == 54) or (r == 100) or (r == 0):
        value[0] = value[0] + 1
      elif (r == 52) or (r == 97) or (r == 113):
        value[0] = value[0] - 1
      elif (r == 103):
        value[0] = value[0] - 30
      elif (r == 104):
        value[0] = value[0] + 30
      elif (r == 102):
        value[0] = value[0] - 100
      elif (r == 106):
        value[0] = value[0] + 100
  cv2.destroyAllWindows()

  firstFrame = int(value[0])
  cap.set(1, max_l)
  ret, frame = cap.read()
  while not(ret):
    max_l = max_l - 1
    cap.set(1, max_l)
    ret, frame = cap.read()
  WINDOW_NAME = "Choose where the sub-video should end."
  WINDOW_NAME_CTRL = "Control"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  cvui.init(WINDOW_NAME_CTRL)
  cv2.moveWindow(WINDOW_NAME_CTRL, 0, 300)
  value = [max_l]
  curValue = value[0]
  buttonclicked = False
  widgetX = 40
  widgetY = 20
  widgetL = 300
  while not(buttonclicked):
      value[0] = int(value[0])
      if curValue != value[0]:
        cap.set(1, value[0])
        frameOld = frame
        ret, frame = cap.read()
        if not(ret):
          frame = frameOld
        curValue = value[0]
      frameCtrl = np.full((200, 400), 100).astype('uint8')
      frameCtrl[widgetY:widgetY+60, widgetX:widgetX+widgetL] = 0
      cvui.text(frameCtrl, widgetX, widgetY, 'Frame')
      cvui.trackbar(frameCtrl, widgetX, widgetY+10, widgetL, value, firstFrame + 1, max_l-1)
      cvui.counter(frameCtrl, widgetX, widgetY+60, value)
      buttonclicked = cvui.button(frameCtrl, widgetX, widgetY+90, "Ok, I want the sub-video to end at this frame!")
      cvui.text(frameCtrl, widgetX, widgetY+130, 'Keys: 4 or a: move backwards; 6 or d: move forward')
      cvui.text(frameCtrl, widgetX, widgetY+160, 'Keys: g or f: fast backwards; h or j: fast forward')
      cvui.imshow(WINDOW_NAME, frame)
      cvui.imshow(WINDOW_NAME_CTRL, frameCtrl)
      r = cv2.waitKey(20)
      if (r == 54) or (r == 100) or (r == 0):
        value[0] = value[0] + 1
      elif (r == 52) or (r == 97) or (r == 113):
        value[0] = value[0] - 1
      elif (r == 103):
        value[0] = value[0] - 30
      elif (r == 104):
        value[0] = value[0] + 30
      elif (r == 102):
        value[0] = value[0] - 100
      elif (r == 106):
        value[0] = value[0] + 100

  lastFrame = int(value[0])
  cv2.destroyAllWindows()
  cap.release()

  # Choosing directory to save sub-video
  directoryChosen = QFileDialog.getExistingDirectory(self.window, 'Choose in which folder you want to save the sub-video.')

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
