import numpy as np
import cv2

ix3, iy3  = -1,-1
ix4, iy4 = -1,-1
ix5, iy5  = -1,-1
ix6, iy6 = -1,-1

# mouse callback function
def getXYCoordinates3(event,x,y,flags,param):
  global ix3,iy3
  if event == cv2.EVENT_LBUTTONDOWN:
    ix3,iy3 = x,y
    
def getXYCoordinates4(event,x,y,flags,param):
  global ix4,iy4
  if event == cv2.EVENT_LBUTTONDOWN:
    ix4,iy4 = x,y

def getXYCoordinates5(event,x,y,flags,param):
  global ix5,iy5
  if event == cv2.EVENT_LBUTTONDOWN:
    ix5,iy5 = x,y

def getXYCoordinates6(event,x,y,flags,param):
  global ix6,iy6
  if event == cv2.EVENT_LBUTTONDOWN:
    ix6,iy6 = x,y

def findWellLeft(frame):
  img = np.zeros((512,512,3), np.uint8)
  cv2.namedWindow('Click on left border')
  cv2.setMouseCallback('Click on left border',getXYCoordinates3)
  while(ix3 == -1):
    cv2.imshow('Click on left border',frame)
    k = cv2.waitKey(20) & 0xFF
    if k == 27:
      break
    elif k == ord('a'):
      print("yeah:",ix3,iy3)
  cv2.destroyAllWindows()
  return [ix3,iy3]

def findWellRight(frame):
  img = np.zeros((512,512,3), np.uint8)
  cv2.namedWindow('Click on right border')
  cv2.setMouseCallback('Click on right border',getXYCoordinates4)
  while(ix4 == -1):
    cv2.imshow('Click on right border',frame)
    k = cv2.waitKey(20) & 0xFF
    if k == 27:
      break
    elif k == ord('a'):
      print("yeah:",ix4,iy4)
  cv2.destroyAllWindows()
  return [ix4,iy4]

def findHeadCenter(frame):
  img = np.zeros((512,512,3), np.uint8)
  cv2.namedWindow('Click on a head center')
  cv2.setMouseCallback('Click on a head center',getXYCoordinates5)
  while(ix5 == -1):
    cv2.imshow('Click on a head center',frame)
    k = cv2.waitKey(20) & 0xFF
    if k == 27:
      break
    elif k == ord('a'):
      print("yeah:",ix5,iy5)
  cv2.destroyAllWindows()
  return [ix5,iy5]

def findBodyExtremity(frame):
  img = np.zeros((512,512,3), np.uint8)
  cv2.namedWindow('Click on the tip of the tail of the same zebrafish')
  cv2.setMouseCallback('Click on the tip of the tail of the same zebrafish',getXYCoordinates6)
  while(ix6 == -1):
    cv2.imshow('Click on the tip of the tail of the same zebrafish',frame)
    k = cv2.waitKey(20) & 0xFF
    if k == 27:
      break
    elif k == ord('a'):
      print("yeah:",ix6,iy6)
  cv2.destroyAllWindows()
  return [ix6,iy6]
