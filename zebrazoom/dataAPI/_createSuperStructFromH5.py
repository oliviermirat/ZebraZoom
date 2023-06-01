import numpy as np


def createSuperStructFromH5(results):
  superStruct = {}
  superStruct["firstFrame"] = results.attrs['firstFrame']
  superStruct['lastFrame'] = results.attrs['lastFrame']
  if 'videoFPS' in results.attrs:
    superStruct['videoFPS'] = results.attrs['videoFPS']
  if 'videoPixelSize' in results.attrs:
    superStruct['videoPixelSize'] = results.attrs['videoPixelSize']
  if 'pathToOriginalVideo' in results.attrs:
    superStruct['pathToOriginalVideo'] = results.attrs['pathToOriginalVideo']
  superStruct['wellPoissMouv'] = []
  for wellIdx in range(len(results['wellPositions'])):
    wellData = []
    superStruct['wellPoissMouv'].append(wellData)
    wellGroup = results[f'dataForWell{wellIdx}']
    for animalIdx, animal in enumerate(wellGroup):
      animalData = []
      wellData.append(animalData)
      dataGroup = wellGroup[animal]['dataPerFrame']
      for bout in wellGroup[animal]['listOfBouts']:
        boutGroup = wellGroup[animal]['listOfBouts'][bout]
        boutData = {'AnimalNumber': animalIdx, 'BoutStart': boutGroup.attrs['BoutStart'], 'BoutEnd': boutGroup.attrs['BoutEnd']}
        animalData.append(boutData)
        for data in boutGroup:
          boutData[data] = boutGroup[data][:].tolist()
        start = boutGroup.attrs['BoutStart'] - superStruct["firstFrame"]
        end = boutGroup.attrs['BoutEnd'] - superStruct["firstFrame"] + 1
        TailX_VideoReferential = np.column_stack([dataGroup['HeadPos']['X']] + [dataGroup['TailPosX'][col] for col in dataGroup['TailPosX'].attrs['columns']])
        TailY_VideoReferential = np.column_stack([dataGroup['HeadPos']['Y']] + [dataGroup['TailPosY'][col] for col in dataGroup['TailPosY'].attrs['columns']])
        boutData['TailX_VideoReferential'] = TailX_VideoReferential[start:end].tolist()
        boutData['TailY_VideoReferential'] = TailY_VideoReferential[start:end].tolist()
        boutData['TailAngle_Raw'] = dataGroup['TailAngle'][start:end].tolist()
        boutData['Heading'] = dataGroup['Heading'][start:end].tolist()
        boutData['HeadX'] = dataGroup['HeadPos']['X'][start:end].tolist()
        boutData['HeadY'] = dataGroup['HeadPos']['Y'][start:end].tolist()
        if 'curvature' in dataGroup:
          boutData['curvature'] = dataGroup['curvature'][start:end].tolist()
  return superStruct
