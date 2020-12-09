import tkinter as tk
from tkinter import Tk, mainloop, TOP
from threading import Timer
import cv2
import cvui
import numpy as np

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

def launchStuff():
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    WINDOW_NAME = "Tracking in Progress"
    cvui.init(WINDOW_NAME)
    cv2.moveWindow(WINDOW_NAME, 0, 0)
    f = open("trace.txt", "r")
    if f.mode == 'r':
      contents = f.read()
    f.close()
    while not("ZebraZoom Analysis finished for" in contents):
      f = open("trace.txt", "r")
      if f.mode == 'r':
        contents = f.read()
      f.close()
      frameCtrl = np.full((400, 500), 100).astype('uint8')
      contentList = contents.split("\n")
      for idx, txt in enumerate(contentList):
        cvui.text(frameCtrl, 4, 15 + idx * 20, txt)
      cvui.imshow(WINDOW_NAME, frameCtrl)
      cv2.waitKey(20)
    cv2.destroyAllWindows()

def initialise():
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    f = open("trace.txt","w+")
    f.write("")
    f.close()
    f = Timer(0.5, launchStuff, ())
    f.start()

def prepend(text):
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    with open("trace.txt", "r+") as f:
      content = f.read()
      f.seek(0, 0)
      f.write(text.rstrip('\r\n') + '\n' + content)
