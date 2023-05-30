from typing import Tuple

from ._openResultsFile import openResultsFile


def getFirstAndLastFrame(videoName: str) -> Tuple[int, int]:
  with openResultsFile(videoName, 'r') as results:
    return results.attrs['firstFrame'], results.attrs['lastFrame']
