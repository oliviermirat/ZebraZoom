from ._openResultsFile import openResultsFile


def setFPSandPixelSize(videoName: str, videoFPS: float, videoPixelSize: float) -> None:

  with openResultsFile(videoName, 'a') as results:
  
    results.attrs['videoFPS']       = videoFPS
    results.attrs['videoPixelSize'] = videoPixelSize
