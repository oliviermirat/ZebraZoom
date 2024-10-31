from ._openResultsFile import openResultsFile


def getNumberOfWells(videoName: str) -> int:
  with openResultsFile(videoName, 'r') as results:
    return len(results['wellPositions'])
