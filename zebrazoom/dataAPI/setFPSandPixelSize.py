import os
import h5py
import numpy as np
from zebrazoom.code.paths import getDefaultZZoutputFolder

def setFPSandPixelSize(videoName: str, videoFPS: float, videoPixelSize: float):
  
  ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  if not os.path.exists(resultsPath):
    raise ValueError(f'video {videoName} not found in the default ZZoutput folder ({ZZoutputPath})')
    
  with h5py.File(resultsPath, 'a') as results:
  
    results.attrs['videoFPS']       = videoFPS
    results.attrs['videoPixelSize'] = videoPixelSize
