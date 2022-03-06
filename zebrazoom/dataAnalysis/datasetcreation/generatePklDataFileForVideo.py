from zebrazoom.code.dataPostProcessing.createPandasDataFrameOfParameters import createPandasDataFrameOfParameters
import pandas as pd
import json
import os

def generatePklDataFileForVideo(excelFileName, ZZoutputLocation, frameStepForDistanceCalculation):
  
  # Generate .pkl data file inside the result video folder if it doesn't already exist
  excelFile = pd.read_excel(excelFileName)
  
  for videoId in range(0, len(excelFile)):
    # If it exists, retrives the frameStepForDistanceCalculationUsed parameter previously used to calculate the distance travelled.
    if os.path.exists(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), 'parametersUsedForCalculation.json')):
      with open(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), 'parametersUsedForCalculation.json')) as json_file:
        parametersUsedForCalculation = json.load(json_file)
    else:
      parametersUsedForCalculation = {}
    
    # Generates the .pkl data file if it doesn't already exist OR if a frameStepForDistanceCalculationUsed different than before is requested or if a videoFPS or videoPixelSize different than before is used
    if not(os.path.exists(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), excelFile.loc[videoId, 'trial_id'] + '.pkl'))) or not(len(parametersUsedForCalculation)) or int(frameStepForDistanceCalculation) != int(parametersUsedForCalculation['frameStepForDistanceCalculation']) or float(excelFile.loc[videoId, 'fq']) != float(parametersUsedForCalculation['videoFPS']) or float(excelFile.loc[videoId, 'pixelsize']) != float(parametersUsedForCalculation['videoFPS']):
      videoName      = excelFile.loc[videoId, 'trial_id']
      videoExtension = os.path.splitext(os.path.split(excelFileName)[1])[1]
      hyperparameters = {}
      hyperparameters["nbWells"] = len(excelFile.loc[0, 'condition'][1:-1].split(','))
      hyperparameters["frameStepForDistanceCalculation"] = frameStepForDistanceCalculation
      hyperparameters["videoFPS"]       = float(excelFile.loc[videoId, 'fq'])
      hyperparameters["videoPixelSize"] = float(excelFile.loc[videoId, 'pixelsize'])
      createPandasDataFrameOfParameters(hyperparameters, videoName, videoExtension, ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'])
