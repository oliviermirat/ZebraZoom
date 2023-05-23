from ._openResultsFile import openResultsFile


def getFPSandPixelSize(videoName: str) -> [float, float]:
  
  with openResultsFile(videoName, 'r') as results:
    videoFPS = results.attrs['videoFPS']
    videoPixelSize = results.attrs['videoPixelSize']
  
  return [videoFPS, videoPixelSize]
