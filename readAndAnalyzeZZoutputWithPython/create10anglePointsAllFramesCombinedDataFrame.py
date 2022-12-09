import pandas as pd
import numpy as np
import json

pathToResultFile = 'results_headEmbeddedZebrafishLarva.txt'

TailX_VideoReferential_All = []
TailY_VideoReferential_All = []
frameNumber_All = []

with open(pathToResultFile) as video:
  supstruct = json.load(video)
  for numWell in range(0, len(supstruct['wellPoissMouv'])):
    for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
      for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
        bout  = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]
        TailX_VideoReferential_All = TailX_VideoReferential_All + bout['TailX_VideoReferential']
        TailY_VideoReferential_All = TailY_VideoReferential_All + bout['TailY_VideoReferential']
        frameNumber_All = frameNumber_All + [i for i in range(bout['BoutStart'], bout['BoutEnd'] + 1)]

TailX_VideoReferential_All = np.array(TailX_VideoReferential_All)
TailY_VideoReferential_All = np.array(TailY_VideoReferential_All)
frameNumber_All            = np.array([frameNumber_All]).transpose()

df = pd.DataFrame(np.concatenate((frameNumber_All, np.concatenate((TailX_VideoReferential_All, TailY_VideoReferential_All), axis=1)), axis=1), columns=['frameNumber'] + ['TailPosX' + str(i) for i in range(1, 11)] + ['TailPosY' + str(i) for i in range(1, 11)])

df.to_excel('10anglePointsForAllBoutsCombined.xlsx')
df.to_pickle('10anglePointsForAllBoutsCombined.pkl')
