import numpy as np
import math

def gatherInitialRawData(dataForBout, rawData, fps):
  
  rawInitialData = []
  
  for param in rawData:
    if param in dataForBout:
      if param in ['Heading', 'TailAngle_Raw', 'TailAngle_smoothed', 'Bend_Amplitude']:
        rawInitialData.append([val * (180 / math.pi) for val in dataForBout[param]])
      elif param == 'TailBeatFrequency':
        if 'Bend_Timing' in dataForBout and type(dataForBout['Bend_Timing']) == list and len(dataForBout['Bend_Timing']):
          TailBeatFrequency = fps / (2 * np.diff([0] + dataForBout['Bend_Timing']))
        else:
          TailBeatFrequency = np.array([])
        rawInitialData.append(TailBeatFrequency.tolist())
      else:
        rawInitialData.append(dataForBout[param])
    else:
      rawInitialData.append(float('nan'))
  
  return rawInitialData
