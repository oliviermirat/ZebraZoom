from zebrazoom.code.dataPostProcessing.createPandasDataFrameOfParameters import createPandasDataFrameOfParameters
from zebrazoom.code.getHyperparameters import getHyperparametersSimple

from ._createSuperStructFromH5 import createSuperStructFromH5
from ._openResultsFile import openResultsFile


def getKinematicParametersPerBout(videoName: str, numWell: int, numAnimal: int, numBout: int) -> dict:
  with openResultsFile(videoName, 'r+') as results:
    animalPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}'
    if animalPath not in results:
      raise ValueError(f"data for animal {numAnimal} in well {numWell} doesn't exist")
    animalGroup = results[animalPath]
    if 'kinematicParametersPerBout' not in animalGroup:
      if 'videoFPS' not in results.attrs:
        raise ValueError(f'videoFPS not found in the results, cannot calculate kinematic parameters')
      if 'videoPixelSize' not in results.attrs:
        raise ValueError(f'videoPixelSize not found in the results, cannot calculate kinematic parameters')
      print(f'calculating and storing kinematic parameters for well {numWell}, animal {numAnimal}, bout {numBout}')
      superStruct = createSuperStructFromH5(results)
      hyperparameters = getHyperparametersSimple(dict(results['configurationFileUsed'].attrs))
      hyperparameters['H5filename'] = results.filename
      hyperparameters['videoFPS'] = results.attrs['videoFPS']
      hyperparameters['videoPixelSize'] = results.attrs['videoPixelSize']
      createPandasDataFrameOfParameters(hyperparameters, '', '', '', superStruct)

    dataset = animalGroup['kinematicParametersPerBout']
    numberOfBouts, = dataset.shape
    if numBout >= numberOfBouts:
      raise ValueError(f"cannot get data for bout {numBout}, total number of detected bouts is {numberOfBouts}")
    return {col: dataset[col][numBout] for col in dataset.attrs['columns']}
