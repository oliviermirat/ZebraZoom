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

class ZzVideoReading():

  def __init__(self, videoPath):
  
    seq_path  = videoPath

    cfg = configparser.ConfigParser()
    cfg.read(seq_path)
    
    width = int(cfg.get('Sequence Settings', 'Width'))
    height = int(cfg.get('Sequence Settings', 'Height'))
    bpp = int(cfg.get('Sequence Settings', 'BytesPerPixel'))
    num_images = cfg.get('Sequence Settings', 'Number of files')
    bin_file = cfg.get('Sequence Settings', 'Bin File')
    sqb_path = seq_path.replace('.seq', '.sqb')
    
    pathstr = os.path.dirname(seq_path)
    
    f = open(sqb_path, 'rb')
    
    self.sqb_path = sqb_path
    self.width = width
    self.height = height
    self.bpp = bpp
    self.num_images = int(num_images)
    self.bin_file = bin_file
    self.sqb_path = sqb_path
    self.pathstr = pathstr
    self.f = f
    self.lastFrameRead = -1
  
  def get(self, idOfInfoRequested):
    
    if idOfInfoRequested == 1:
      return self.lastFrameRead + 1
    elif idOfInfoRequested == 3:
      return self.width
    elif idOfInfoRequested == 4:
      return self.height
    elif idOfInfoRequested == 7:
      return self.num_images
    elif idOfInfoRequested == 5:
      return 24 # fake input video fps
  
  def isOpened(self):
    return True
  
  def release(self):
    del self
    
  def read(self):
    
    if self.lastFrameRead + 1 < self.num_images:
      
      if int(platform.system() == "Linux"):
        try:
          offset = struct.unpack('l', self.f.read(8))
          timestamp = struct.unpack('d', self.f.read(8))
          binfile = struct.unpack('i', self.f.read(4))
          padding = self.f.read(4)
        except:
          print("Problem with Hiris video format", self.lastFrameRead + 1)
          return [False, []]
      else:
        try:
          offset = struct.unpack('l', self.f.read(4))
          padding = self.f.read(4)
          timestamp = struct.unpack('d', self.f.read(8))
          binfile = struct.unpack('i', self.f.read(4))
          padding = self.f.read(4)
        except:
          print("Problem with Hiris video format", self.lastFrameRead + 1)
          return [False, []]          
      
      bin_path = os.path.join("%s" % (self.pathstr), "%s%0.5d.bin" % (self.bin_file, binfile[0]))
      
      if not(os.path.exists(bin_path)):
        print("Hiris video format: frame not found:", self.lastFrameRead + 1)
        return [False, []]
      
      f_bin = open(bin_path, 'rb')
      f_bin.seek(offset[0], os.SEEK_SET)
      
      bytes = f_bin.read(self.height*self.width*self.bpp)
      
      if self.bpp == 2:
        buffer = np.frombuffer(bytes, dtype=np.uint16)
      else:
        buffer = np.frombuffer(bytes, dtype=np.uint8)
      
      
      if len(buffer) == 3*self.height*self.width:
        nparr2 = buffer.reshape(self.height, self.width, 3)
      else:
        nparr2 = buffer.reshape(self.height, self.width)
        nparr2 = cv2.cvtColor(nparr2, cv2.COLOR_GRAY2RGB)
      
      self.lastFrameRead = self.lastFrameRead + 1
      
      return [True, nparr2]
    
    else:
      
      return [False, []]
  
  
  def set(self, propToChange, numImage):
    
    if propToChange == 1:
      
      if numImage <= 0:
        
        self.f.close()
        self.f = open(self.sqb_path, 'rb')
        self.lastFrameRead = -1
      
      elif numImage >= self.num_images:
        
        self.lastFrameRead = int(self.num_images)
        
      elif numImage > self.lastFrameRead:
        
        justToMove = self.f.read(24 * (int(numImage) - int(self.lastFrameRead) - 1))
        self.lastFrameRead = numImage - 1  
        
      elif numImage < self.lastFrameRead:
        
        self.f.close()
        self.f = open(self.sqb_path, 'rb')
        
        justToMove = self.f.read(24 * int(numImage))
        self.lastFrameRead = numImage - 1


def VideoCapture(videoPath):
  
  if '.seq' in videoPath:
    
    zzVidCapture = ZzVideoReading(videoPath)
    
    return zzVidCapture
  
  elif '.sqb' in videoPath:
    
    zzVidCapture = ZzVideoReading(videoPath.replace('.sqb', '.seq'))
    
    return zzVidCapture
  
  else:
    
    return cv2.VideoCapture(videoPath)
