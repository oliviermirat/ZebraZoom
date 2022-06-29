import struct
import csv
import mmap
import datetime
import array
import logging
import os
import csv
import glob
import time
import configparser
import numpy as np
import cv2
from pathlib import Path
import platform

def sqb_convert_to_avi(path, videoName, codec='HFYU', lastFrame=-1):
  """
      Lecture du fichier binaire de séquence sqb
      Les données sont représentées par la structure en C suivante :
          typedef struct
          {   
              long offset;        // 4 bits -> + 4 bits vides car mémoire alignée
              double TimeStamp;   // 8 bits
              int binfile;        // 4 bits -> + 4 bits vides car mémoire alignée
          } IMGDATA;
  """
  
  # Checking that path and video exists
  if not(os.path.exists(os.path.join(path, videoName + '.seq'))):
    print("Path or video name is incorrect for", os.path.join(path, videoName + '.seq'))
    return 0
  
  seq_path  = os.path.join(path, videoName + '.seq')
  path2 = Path(path)
  avi_path  = os.path.join(path2.parent, videoName + '.avi')

  cfg = configparser.ConfigParser()
  cfg.read(seq_path)
  
  width = int(cfg.get('Sequence Settings', 'Width'))
  height = int(cfg.get('Sequence Settings', 'Height'))
  bpp = int(cfg.get('Sequence Settings', 'BytesPerPixel'))
  num_images = cfg.get('Sequence Settings', 'Number of files')
  bin_file = cfg.get('Sequence Settings', 'Bin File')
  sqb_path = seq_path.replace('.seq', '.sqb')
  
  out = cv2.VideoWriter(avi_path, cv2.VideoWriter_fourcc(codec[0],codec[1],codec[2],codec[3]), 10, (width, height))
  
  pathstr = os.path.dirname(seq_path)
  if lastFrame <= 0:
    lastFrame = int(num_images)
  
  with open(sqb_path,'rb') as f :
    for i in range(0, lastFrame):
    
      if (i % 500 == 0):
        print("image " + str(i) + " out of " + str(lastFrame) + " in total")
    
      if int(platform.system() == "Linux"):
        offset = struct.unpack('l', f.read(8))
        timestamp = struct.unpack('d', f.read(8))
        binfile = struct.unpack('i', f.read(4))
        padding = f.read(4)
      else:
        offset = struct.unpack('l', f.read(4))
        padding = f.read(4)
        timestamp = struct.unpack('d', f.read(8))
        binfile = struct.unpack('i', f.read(4))
        padding = f.read(4)
      
      bin_path = os.path.join("%s" % (pathstr), "%s%0.5d.bin" % (bin_file, binfile[0]))
      
      f_bin = open(bin_path, 'rb')
      f_bin.seek(offset[0], os.SEEK_SET)
      
      bytes = f_bin.read(height*width*bpp)
      
      if bpp == 2:
        buffer = np.frombuffer(bytes, dtype=np.uint16)
      else:
        buffer = np.frombuffer(bytes, dtype=np.uint8)
      
      if len(buffer) == 3*height*width:
        nparr2 = buffer.reshape(height, width, 3)
      else:
        nparr2 = buffer.reshape(height, width)
        nparr2 = cv2.cvtColor(nparr2, cv2.COLOR_GRAY2RGB)
        
      out.write(nparr2)
      
      f_bin.close()
      
  out.release()
