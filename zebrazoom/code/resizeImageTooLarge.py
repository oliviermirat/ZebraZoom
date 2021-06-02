import tkinter as tk
import cv2
import numpy as np

def resizeImageTooLarge(frame, fillScreen=False):
  root = tk.Tk()
  horizontal = root.winfo_screenwidth()
  vertical   = root.winfo_screenheight()
  root.destroy()
  getRealValueCoefX = 1
  getRealValueCoefY = 1
  if len(frame[0]) > horizontal or len(frame) > vertical:
    reduce = min((horizontal / len(frame[0])) * 0.98, (vertical / len(frame)) * 0.95)
    newLengthX = int(len(frame[0]) * reduce)
    newLengthY = int(len(frame)    * reduce)
    getRealValueCoefX = len(frame[0]) / newLengthX
    getRealValueCoefY = len(frame)    / newLengthY
    frame = cv2.resize(frame, (newLengthX, newLengthY))
  
  if fillScreen:
    frame2 = np.zeros((vertical, horizontal, len(frame[0][0])))
    frame2 = frame2.astype(np.uint8)
    frame2[0:len(frame), 0:len(frame[0])] = frame
    frame = frame2
  
  return [frame, getRealValueCoefX, getRealValueCoefY, horizontal, vertical]
