import os
import h5py
import numpy as np
from zebrazoom.code.paths import getDefaultZZoutputFolder

def getFPSandPixelSize(videoName: str):
  
  ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  
  if not os.path.exists(resultsPath):
    raise ValueError(f'video {videoName} not found in the default ZZoutput folder ({ZZoutputPath})')
    
  with h5py.File(resultsPath, 'r+') as results:  
    videoFPS = results.attrs['videoFPS']
    videoPixelSize = results.attrs['videoPixelSize']
  
  return [videoFPS, videoPixelSize]
