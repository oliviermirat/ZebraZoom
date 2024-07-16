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
  superStruct['wellPositions'] = [dict(results[f'wellPositions/well{idx}'].attrs) for idx in range(len(results['wellPositions']))]
  for wellIdx in range(len(superStruct['wellPositions'])):
    wellData = []
    superStruct['wellPoissMouv'].append(wellData)
    wellGroup = results[f'dataForWell{wellIdx}']
    for animalIdx in range(len(wellGroup)):
      animalGroup = wellGroup[f'dataForAnimal{animalIdx}']
      animalData = []
      wellData.append(animalData)
      if 'dataPerFrame' not in animalGroup:
        continue
      dataGroup = animalGroup['dataPerFrame']
      HeadPos = dataGroup['HeadPos'][:]
      TailPosX = dataGroup['TailPosX'][:]
      TailPosY = dataGroup['TailPosY'][:]
      TailX_VideoReferential = np.column_stack([HeadPos['X']] + [TailPosX[col] for col in dataGroup['TailPosX'].attrs['columns']])
      TailY_VideoReferential = np.column_stack([HeadPos['Y']] + [TailPosY[col] for col in dataGroup['TailPosY'].attrs['columns']])
      TailAngle = dataGroup['TailAngle'][:]
      Heading = dataGroup['Heading'][:]
      curvature = None if 'curvature' not in dataGroup else dataGroup['curvature'][:]
      for boutIdx in range(animalGroup['listOfBouts'].attrs['numberOfBouts']):
        boutGroup = animalGroup[f'listOfBouts/bout{boutIdx}']
        boutData = {'AnimalNumber': animalIdx, 'BoutStart': boutGroup.attrs['BoutStart'], 'BoutEnd': boutGroup.attrs['BoutEnd']}
        if boutGroup.attrs.get('flag'):
          boutData['flag'] = 1
        animalData.append(boutData)
        for data in boutGroup:
          if data == 'additionalKinematicParametersPerBout':
            continue
          boutData[data] = boutGroup[data][:].tolist()
        start = boutGroup.attrs['BoutStart'] - superStruct["firstFrame"]
        end = boutGroup.attrs['BoutEnd'] - superStruct["firstFrame"] + 1
        boutData['TailX_VideoReferential'] = TailX_VideoReferential[start:end].tolist()
        boutData['TailY_VideoReferential'] = TailY_VideoReferential[start:end].tolist()
        boutData['TailAngle_Raw'] = TailAngle[start:end].tolist()
        boutData['Heading'] = Heading[start:end].tolist()
        boutData['HeadX'] = HeadPos['X'][start:end].tolist()
        boutData['HeadY'] = HeadPos['Y'][start:end].tolist()
        if curvature is not None:
          boutData['curvature'] = curvature[start:end].tolist()
  return superStruct
