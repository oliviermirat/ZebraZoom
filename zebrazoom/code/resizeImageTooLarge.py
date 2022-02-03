import tkinter as tk
import cv2
import numpy as np

def resizeImageTooLarge(frame, fillScreen=True, horizontalReduction=0.98, verticalReduction=0.95):
  root = tk.Tk()
  horizontal = root.winfo_screenwidth()
  vertical   = root.winfo_screenheight()
  root.destroy()
  getRealValueCoefX = 1
  getRealValueCoefY = 1
  if len(frame[0]) > horizontal or len(frame) > vertical:
    reduce = min((horizontal / len(frame[0])) * horizontalReduction, (vertical / len(frame)) * verticalReduction)
    newLengthX = int(len(frame[0]) * reduce)
    newLengthY = int(len(frame)    * reduce)
    getRealValueCoefX = len(frame[0]) / newLengthX
    getRealValueCoefY = len(frame)    / newLengthY
    frame = cv2.resize(frame, (newLengthX, newLengthY))
  if fillScreen:
    if type(frame[0][0]) == np.uint8:
      frame2 = np.zeros((vertical, horizontal))
    else:
      frame2 = np.zeros((vertical, horizontal, len(frame[0][0])))
    frame2 = frame2.astype(np.uint8)
    frame2[0:len(frame), 0:len(frame[0])] = frame
    frame = frame2
  return [frame, getRealValueCoefX, getRealValueCoefY, horizontal, vertical]