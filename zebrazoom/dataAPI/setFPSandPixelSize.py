from ._openResultsFile import openResultsFile


def setFPSandPixelSize(videoName: str, videoFPS: float, videoPixelSize: float) -> None:

  with openResultsFile(videoName, 'a') as results:
    if videoFPS == results.attrs.get('videoFPS') and videoPixelSize == results.attrs.get('videoPixelSize'):
      return
    results.attrs['videoFPS']       = float(videoFPS)
    results.attrs['videoPixelSize'] = float(videoPixelSize)

    # if kinematic parameters were calculated, remove them since they are no longer valid
    for wellIdx in range(len(results['wellPositions'])):
      wellGroup = results[f'dataForWell{wellIdx}']
      for animal in wellGroup:
        animalGroup = wellGroup[animal]
        if 'kinematicParametersPerBout' in animalGroup:
          del animalGroup['kinematicParametersPerBout']
        if 'listOfBouts' in animalGroup:
          for bout in animalGroup['listOfBouts']:
            boutGroup = animalGroup[f'listOfBouts/{bout}']
            if 'additionalKinematicParametersPerBout' in boutGroup:
              del boutGroup['additionalKinematicParametersPerBout']
    if 'frameStepForDistanceCalculation' in results.attrs:
      del results.attrs['frameStepForDistanceCalculation']
