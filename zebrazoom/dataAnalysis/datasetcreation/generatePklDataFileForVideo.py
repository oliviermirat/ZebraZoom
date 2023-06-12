from zebrazoom.code.dataPostProcessing.createPandasDataFrameOfParameters import createPandasDataFrameOfParameters
import h5py
import pandas as pd
import json
import os


def _getParametersUsedForCalculation(path, trialID, ZZoutputLocation):
  rootPath = os.path.join(ZZoutputLocation if path == "defaultZZoutputFolder" else path, trialID)
  if os.path.splitext(trialID)[1] != '.h5':
    parametersPath = os.path.join(rootPath, f'{trialID}.pkl')
    if not os.path.exists(parametersPath):
      return {}
    parametersUsedForCalculationPath = os.path.join(rootPath, 'parametersUsedForCalculation.json')
    if not os.path.exists(parametersUsedForCalculationPath):
      return {}
    with open(parametersUsedForCalculationPath) as f:
      return json.load(f)
  else:
    with h5py.File(rootPath, 'r') as results:
      videoFPS = results.attrs.get('videoFPS', None)
      videoPixelSize = results.attrs.get('videoPixelSize', None)
      frameStepForDistanceCalculation = results.attrs.get('frameStepForDistanceCalculation', None)
    parametersUsedForCalculation = {}
    if videoFPS is not None:
      parametersUsedForCalculation['videoFPS'] = float(videoFPS)
    if videoPixelSize is not None:
      parametersUsedForCalculation['videoPixelSize'] = float(videoPixelSize)
    if frameStepForDistanceCalculation is not None:
      parametersUsedForCalculation['frameStepForDistanceCalculation'] = int(frameStepForDistanceCalculation)
    return parametersUsedForCalculation


def generatePklDataFileForVideo(excelFileName, ZZoutputLocation, frameStepForDistanceCalculation, forcePandasRecreation=0, reusingParametersCb=None):
  
  # Generate .pkl data file inside the result video folder if it doesn't already exist
  excelFile = pd.read_excel(excelFileName)
  
  for videoId in range(0, len(excelFile)):
    # If it exists, retrives the frameStepForDistanceCalculationUsed parameter previously used to calculate the distance travelled.
    newParametersUsedForCalculation = {'videoFPS': float(excelFile.loc[videoId, 'fq']), 'videoPixelSize': float(excelFile.loc[videoId, 'pixelsize']), 'frameStepForDistanceCalculation': int(frameStepForDistanceCalculation)}
    parametersUsedForCalculation = _getParametersUsedForCalculation(excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id'], ZZoutputLocation)
    
    # Generates the .pkl data file if it doesn't already exist OR if a frameStepForDistanceCalculationUsed different than before is requested or if a videoFPS or videoPixelSize different than before is used
    regenerate = forcePandasRecreation or parametersUsedForCalculation != newParametersUsedForCalculation
    if not regenerate and reusingParametersCb is not None:
      forcePandasRecreation = reusingParametersCb()
      regenerate = forcePandasRecreation
      reusingParametersCb = None

    if regenerate and os.path.splitext(excelFile.loc[videoId, 'trial_id'])[1] != '.h5':
      print("Generating pkl datafile for video " + excelFile.loc[videoId, 'trial_id'] + " , because:")
      if not(os.path.exists(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), excelFile.loc[videoId, 'trial_id'] + '.pkl'))):
        print("the path", os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), excelFile.loc[videoId, 'trial_id'] + '.pkl'), "does not exist")
      if not(len(parametersUsedForCalculation)):
        print("len(parametersUsedForCalculation) is equal to", len(parametersUsedForCalculation))
      else:
        if int(frameStepForDistanceCalculation) != int(parametersUsedForCalculation['frameStepForDistanceCalculation']):
          print("int(frameStepForDistanceCalculation)=", int(frameStepForDistanceCalculation), "and: int(parametersUsedForCalculation['frameStepForDistanceCalculation']=", int(parametersUsedForCalculation['frameStepForDistanceCalculation']))
        if float(excelFile.loc[videoId, 'fq']) != float(parametersUsedForCalculation['videoFPS']):
          print("float(excelFile.loc[videoId, 'fq'])", float(excelFile.loc[videoId, 'fq']), "float(parametersUsedForCalculation['videoFPS']):", float(parametersUsedForCalculation['videoFPS']))
        if float(excelFile.loc[videoId, 'pixelsize']) != float(parametersUsedForCalculation['videoFPS']):
          print("float(excelFile.loc[videoId, 'pixelsize'])", float(excelFile.loc[videoId, 'pixelsize']), "float(parametersUsedForCalculation['videoPixelSize'])", float(parametersUsedForCalculation['videoPixelSize']))
      
      videoName      = excelFile.loc[videoId, 'trial_id']
      videoExtension = os.path.splitext(os.path.split(excelFileName)[1])[1]
      hyperparameters = {}
      hyperparameters["nbWells"] = len(excelFile.loc[videoId, 'condition'][1:-1].split(','))
      hyperparameters["frameStepForDistanceCalculation"] = frameStepForDistanceCalculation
      hyperparameters["videoFPS"]       = float(excelFile.loc[videoId, 'fq'])
      hyperparameters["videoPixelSize"] = float(excelFile.loc[videoId, 'pixelsize'])
      createPandasDataFrameOfParameters(hyperparameters, videoName, videoExtension, ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'])
  return forcePandasRecreation