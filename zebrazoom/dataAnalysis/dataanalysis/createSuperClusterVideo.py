import cv2
import numpy as np

import zebrazoom.code.util as util


folderName = 'allCatamaran'

cap1 = zzVideoReading.VideoCapture(folderName + '/cluster1.avi')
cap2 = zzVideoReading.VideoCapture(folderName + '/cluster3.avi')
cap3 = zzVideoReading.VideoCapture(folderName + '/cluster4.avi')
cap4 = zzVideoReading.VideoCapture(folderName + '/cluster5.avi')

frame_width  = int(cap1.get(3))
frame_height = int(cap1.get(4))
max1         = int(cap1.get(7))
max2         = int(cap2.get(7))
max3         = int(cap3.get(7))
max4         = int(cap4.get(7))
minOfMaxs    = min(max1, min(max2, min(max3, max4)))

out = cv2.VideoWriter('outpy.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 10, (2*frame_width, 2*frame_height))
# out = cv2.VideoWriter('outpy.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 10, (frame_width, frame_height))

affiche = False

i = 0
# Read until video is completed
while(cap1.isOpened() and (i < minOfMaxs - 1)):
  i = i + 1
  # Capture frame-by-frame
  ret, frame1 = cap1.read()
  ret, frame2 = cap2.read()
  ret, frame3 = cap3.read()
  ret, frame4 = cap4.read()
  
  if ret == True:
    # frameF = np.zeros((2*frame_width, 2*frame_height, 3))
    # frameF[0:frame_height,              0:frame_width]             = frame1
    # frameF[0:frame_height,              frame_width:2*frame_width] = frame2
    # frameF[frame_height:2*frame_height, 0:frame_width]             = frame3
    # frameF[frame_height:2*frame_height, frame_width:2*frame_width] = frame4

    # frameF = np.zeros((frame_width, frame_height, 3))
    # frameF[0:frame_height, 0:frame_width] = frame1
    fl1    = np.concatenate((frame1, frame2), axis=1)
    fl2    = np.concatenate((frame3, frame4), axis=1)
    frameF = np.concatenate((fl1, fl2), axis=0)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    ydown = 13
    fontSize = 0.4
    cv2.putText(frameF,"Cluster 1:",(int(1),int(10)),font,fontSize,(255,255,255))
    cv2.putText(frameF,"Slow Forward Swims",(int(1),int(10+ydown)),font,fontSize,(255,255,255))
    
    cv2.putText(frameF,"Cluster 2:",(int(2+frame_width),int(10)),font,fontSize,(255,255,255))
    cv2.putText(frameF,"Small Amplitude Turns",(int(2+frame_width),int(10+ydown)),font,fontSize,(255,255,255))
    
    cv2.putText(frameF,"Cluster 3:",(int(1),int(frame_height+11)),font,fontSize,(255,255,255))
    cv2.putText(frameF,"Large Amplitude Turns",(int(1),int(frame_height+11+ydown)),font,fontSize,(255,255,255))
    
    cv2.putText(frameF,"Cluster 4:",(int(2+frame_width),int(frame_height+11)),font,fontSize,(255,255,255))
    cv2.putText(frameF,"Burst Swims",(int(2+frame_width),int(frame_height+11+ydown)),font,fontSize,(255,255,255))
    
    lineThickness = 1
    cv2.line(frameF, (frame_width, 0),  (frame_width, 2*frame_height), (255,255,255), lineThickness)
    cv2.line(frameF, (0, frame_height), (2*frame_width, frame_height), (255,255,255), lineThickness)
    
    if (affiche):
      # Display the resulting frame
      util.showFrame(frameF, title='Frame')
    else:
       out.write(frameF)
 
  # Break the loop
  else: 
    break

# When everything done, release the video capture object
cap1.release()
cap2.release()
cap3.release()
cap4.release()
 
# Closes all the frames
cv2.destroyAllWindows()
