import pandas as pd
import numpy as np

nbWells = 100

# nbOscillation = [3.19, 0.01]
# tbf           = [24.29, 0.03]
boutDuration  = [0.1895, 0.05]
# heading       = [51.14, 0.18]
distance      = [2.49, 2]
speed         = [13.35, 20]
# boutFrequency = [0.4495, 0.0117]

boutDurationValues = np.random.normal(boutDuration[0], boutDuration[1], 100)
distanceValues     = np.random.normal(distance[0],     distance[1],     100)
speedValues        = np.random.normal(speed[0],        speed[1],        100)

videoDurationValues = np.random.normal(1, 0.1, 100)

data = pd.DataFrame(data=[["standardValueFreelySwimZebrafishLarvae", i, i, 5, 50, 1, 'StandardValue', videoDurationValues[i], boutDurationValues[i], distanceValues[i], speedValues[i]] for i in range(nbWells)], columns=['Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration', 'BoutDuration', 'TotalDistance', 'Speed'])

data.to_pickle('standardValueFreelySwimZebrafishLarvae.pkl')
