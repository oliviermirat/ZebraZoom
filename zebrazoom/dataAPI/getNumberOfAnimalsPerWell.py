from ._openResultsFile import openResultsFile


def getNumberOfAnimalsPerWell(videoName: str) -> int:
  with openResultsFile(videoName, 'r') as results:
    return len(results['dataForWell0'])
