import h5py
import numpy as np
import cv2
import math
import json
import sys
from scipy import interpolate
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from scipy.interpolate import UnivariateSpline
from numpy import linspace

def Rotate(boundary, aaa, bbb, angle, dst):

  gauche = 0
  haut   = 0

  x1 = aaa + 100*math.cos(angle)
  y1 = bbb + 100*math.sin(angle)
  x2 = aaa + 100*math.cos(angle + math.pi)
  y2 = bbb + 100*math.sin(angle + math.pi)
  x = 0
  y = 0
  r = 0
  Yoo = [x1 + gauche,y1 + haut]
  Yaa = [x2 + gauche,y2 + haut]

  dist1 = 0
  min_dist1 = 1000000
  dist2 = 0
  min_dist2 = 1000000
  theta = 0
  alpha = 0
  alpha_aux = 0
  final_angle = 0
  for i in range(0, len(boundary)):
    Pt = boundary[i][0]
    dist1 = (Pt[0] - x1)*(Pt[0] - x1) + (Pt[1] - y1)*(Pt[1] - y1)
    dist2 = (Pt[0] - x2)*(Pt[0] - x2) + (Pt[1] - y2)*(Pt[1] - y2)
    if (dist1<min_dist1):
      min_dist1 = dist1
    if (dist2<min_dist2):
      min_dist2 = dist2

  if (min_dist1<min_dist2):
    theta = angle
  else:
    theta = angle + math.pi

  theta = (math.pi/2) - theta

  for i in range(0, len(boundary)):
    Pt = boundary[i][0]
    x = Pt[0]
    y = Pt[1]
    x = x - aaa
    y = y - bbb
    r = math.sqrt(x*x + y*y)
    if (x>0):
      alpha = math.atan(y/x)
    if (x<0):
      x = -x
      alpha_aux = math.atan(y/x)
      alpha = math.pi - alpha_aux
    if (x == 0):
      if (y>0):
        alpha = math.pi/2
      else:
        alpha = -math.pi/2

    final_angle = theta + alpha
    x = r*math.cos(final_angle)
    y = r*math.sin(final_angle)
    Pt[0] = x + aaa
    Pt[1] = y + bbb + 200
    
    boundary[i] = Pt
    
  return boundary
