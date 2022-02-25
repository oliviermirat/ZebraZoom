from zebrazoom.code.dataPostProcessing.createPandasDataFrameOfParameters import createPandasDataFrameOfParameters
import pandas as pd
import os

def generatePklDataFileForVideo(excelFileName, ZZoutputLocation, frameStepForDistanceCalculation):
  
  # Generate .pkl data file inside the result video folder if it doesn't already exist
  excelFile = pd.read_excel(excelFileName)
  
  for videoId in range(0, len(excelFile)):
    # If it exists, retrives the frameStepForDistanceCalculationUsed parameter previously used to calculate the distance travelled.
    if os.path.exists(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), 'frameStepForDistanceCalculationUsed.json')):
      file1 = open(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), 'frameStepForDistanceCalculationUsed.json'), "r+")
      frameStepForDistanceCalculationUsed = int(file1.read())
      file1.close()
    else:
      frameStepForDistanceCalculationUsed = frameStepForDistanceCalculation
    # Generates the .pkl data file if it doesn't already exist OR if a frameStepForDistanceCalculationUsed different than before is requested
    
    if not(os.path.exists(os.path.join(os.path.join(ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id']), excelFile.loc[videoId, 'trial_id'] + '.pkl'))) or int(frameStepForDistanceCalculation) != int(frameStepForDistanceCalculationUsed):
      videoName      = excelFile.loc[videoId, 'trial_id']
      videoExtension = os.path.splitext(os.path.split(excelFileName)[1])[1]
      hyperparameters = {}
      hyperparameters["nbWells"] = len(excelFile.loc[0, 'condition'][1:-1].split(','))
      hyperparameters["frameStepForDistanceCalculation"] = frameStepForDistanceCalculation
      hyperparameters["videoFPS"]       = float(excelFile.loc[videoId, 'fq'])
      hyperparameters["videoPixelSize"] = float(excelFile.loc[videoId, 'pixelsize'])
      createPandasDataFrameOfParameters(hyperparameters, videoName, videoExtension, ZZoutputLocation if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder" else excelFile.loc[videoId, 'path'])
