from ._openResultsFile import openResultsFile


def listAllBouts(videoName: str, numWell: int, numAnimal: int, seconds: bool=False):
  with openResultsFile(videoName, 'r') as results:
    boutsPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'
    if boutsPath not in results:
      raise ValueError(f"bouts not found for animal {numAnimal} in well {numWell}")
    boutsGroup = results[boutsPath]
    boutTimings = ((boutsGroup[f'bout{boutIdx}'].attrs['BoutStart'], boutsGroup[f'bout{boutIdx}'].attrs['BoutEnd']) for boutIdx in range(boutsGroup.attrs['numberOfBouts']))
    if not seconds:
      return list(boutTimings)
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert frames to seconds')
    videoFPS = results.attrs['videoFPS']
    return [(start / videoFPS, end / videoFPS) for start, end in boutTimings]
