from typing import Tuple

from ._openResultsFile import openResultsFile


def getWellCoordinates(videoName: str, numWell: int) -> Tuple[int, int, int, int]:
  with openResultsFile(videoName, 'r') as results:
    return results["wellPositions/well" + str(numWell)].attrs["topLeftX"], results["wellPositions/well" + str(numWell)].attrs["topLeftY"], results["wellPositions/well" + str(numWell)].attrs["lengthX"], results["wellPositions/well" + str(numWell)].attrs["lengthY"]
