import zebrazoom.dataAPI as dataAPI
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

### Parameters to change

usingHdf5format = False
videoFPS = 160

if usingHdf5format:
  videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/23.05.19.ao-07-f-1-2-long1_2023_10_02-11_47_42.h5"
  keepOnlyBouts = True
  removeSuspiciousFrames = True
  tailLenghtMaxThresh = 0.1
  tailAngleDiffLowerThresh = 0.1
  tailAngleDiffUpperThresh = 0.3
  useOnlyTailAngleVariationForFrameRemoval = True
else:
  excelData = ["../zebrazoom/ZZoutput/23.05.19.ao-07-f-1-2-long1_2023_10_01-08_55_57/allData_23.05.19.ao-07-f-1-2-long1_wellNumber0_animal0.csv", "../zebrazoom/ZZoutput/23.05.19.ao-07-f-1-2-long1_2023_10_01-08_55_57/allData_23.05.19.ao-07-f-1-2-long1_wellNumber0_animal1.csv"]
  keepOnlyBouts = True
  removeSuspiciousFrames = True
  tailLenghtMaxThresh = 0.1
  tailAngleDiffLowerThresh = 0
  tailAngleDiffUpperThresh = 0.4
  useOnlyTailAngleVariationForFrameRemoval = True

####

def getMinMaxDiffWithinSegment(nparray, startSegment, segmentLength):
  return max(nparray[startSegment:startSegment+segmentLength]) - min(nparray[startSegment:startSegment+segmentLength])

if usingHdf5format:
  videoPixelSize = 0.01
  dataAPI.setFPSandPixelSize(videoName, videoFPS, videoPixelSize)
  startTimeInSeconds = 0 #0.00625
  endTimeInSeconds   = 600

numWell = 0

for numAnimal in [0, 1]:

  print("")
  print("Animal Number:", numAnimal)

  if usingHdf5format:
    TailAngle0  = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "TailAngle")
    TailLength0 = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "TailLength")
    boutTimings = dataAPI.listAllBouts(videoName, numWell, numAnimal)
  else:
    pandasData = pd.read_csv(excelData[numAnimal])
    TailAngle0  = pandasData["tailAngle"].to_numpy()
    TailLength0 = pandasData["TailLength"].to_numpy()

  FrameNumber0 = np.array([i for i in range(len(TailAngle0))])
  totalLength0 = 0
  if usingHdf5format:
    for timing in boutTimings:
      totalLength0 += timing[1] - timing[0]
    print("percentage of time spent swimming:", totalLength0 / (10 * 60 * videoFPS))
  if keepOnlyBouts:
    if usingHdf5format:
      TailAngle0b   = np.array([])
      TailLength0b  = np.array([])
      FrameNumber0b = np.array([])
      for timing in boutTimings:
        TailAngle0b   = np.append(TailAngle0b,  TailAngle0[timing[0]:timing[1]])
        TailLength0b  = np.append(TailLength0b, TailLength0[timing[0]:timing[1]])
        FrameNumber0b = np.append(FrameNumber0b, FrameNumber0[timing[0]:timing[1]])
      TailAngle0   = TailAngle0b
      TailLength0  = TailLength0b
      FrameNumber0 = FrameNumber0b
    else:
      TailAngle0   = pandasData[pandasData["BoutNumber"].isna() == False]["tailAngle"].to_numpy()
      TailLength0  = pandasData[pandasData["BoutNumber"].isna() == False]["TailLength"].to_numpy()
      FrameNumber0 = pandasData[pandasData["BoutNumber"].isna() == False].index.to_numpy()
    print("Total number of frames:", (10 * 60 * videoFPS), "; Frames spent swimming:", len(TailAngle0), "; Percentage of time spent swimming:", len(TailAngle0) / (10 * 60 * videoFPS))
    
  TailAngle0saved = TailAngle0.copy()
    
  tailAngleDiffAbs0 = np.append(np.array([getMinMaxDiffWithinSegment(TailAngle0, i, 10) for i in range(0, len(TailAngle0) - 10)]), np.array([getMinMaxDiffWithinSegment(TailAngle0, len(TailAngle0) - 10, 10) for i in range(0, 10)]))

  TailLength0 = abs(np.append(np.diff(TailLength0), np.array([0])))

  TailAngle0 = TailAngle0 - min(TailAngle0)
  TailAngle0 = TailAngle0 / max(TailAngle0)
  tailAngleDiffAbs0 = tailAngleDiffAbs0 - min(tailAngleDiffAbs0)
  tailAngleDiffAbs0 = tailAngleDiffAbs0 / max(tailAngleDiffAbs0)
  TailLength0 = TailLength0 - min(TailLength0)
  TailLength0 = TailLength0 / max(TailLength0)
  if removeSuspiciousFrames:
    originalNb = len(TailAngle0)
    TailAngle0BeforeRemoval = TailAngle0.copy()
    TailAngle0savedBeforeRemoval = TailAngle0saved.copy()
    FrameNumberNoInterBout = np.array([i for i in range(originalNb)])
    if useOnlyTailAngleVariationForFrameRemoval:
      toRemove0 = (np.convolve(tailAngleDiffAbs0 > tailAngleDiffUpperThresh, np.ones(10), mode='same') != 0)
    else:
      toRemove0 = np.logical_or(np.logical_or(np.convolve(TailLength0 > tailLenghtMaxThresh, np.ones(10), mode='same') != 0, np.convolve(tailAngleDiffAbs0 < tailAngleDiffLowerThresh, np.ones(10), mode='same') != 0), np.convolve(tailAngleDiffAbs0 > tailAngleDiffUpperThresh, np.ones(10), mode='same') != 0)
    TailAngle0 = TailAngle0[toRemove0 == False]
    TailAngle0saved = TailAngle0saved[toRemove0 == False]
    tailAngleDiffAbs0 = tailAngleDiffAbs0[toRemove0 == False]
    TailLength0 = TailLength0[toRemove0 == False]
    FrameNumber0 = FrameNumber0[toRemove0 == False]
    FrameNumberNoInterBout = FrameNumberNoInterBout[toRemove0 == False]
    newNb = len(TailAngle0)
    print("Original number of frames:", originalNb, "; New number of frames:", newNb, "; Percentage of frames kept:", (newNb/originalNb)*100)
  plt.plot(TailAngle0)
  plt.plot(tailAngleDiffAbs0, color='#F6A11A') # Orange
  if not(useOnlyTailAngleVariationForFrameRemoval):
    plt.plot(TailLength0, color='#5BBB32')     # Green
  plt.show()

  # Fourrier transform
  N = len(TailAngle0saved)
  T = 1/160
  xf = fftfreq(N, T)[:N//2]
  yf0 = fft(TailAngle0saved)
  plt.plot(xf, 2.0/N * np.abs(yf0[0:N//2]))
  plt.grid()
  plt.show()

  # Exporting frames kept
  df = pd.DataFrame({'FrameNumber': FrameNumber0})
  df = df.sort_values(by='FrameNumber')
  df.to_excel("framesKept" + str(numAnimal) + ".xlsx", index=False)

  ###
  if True:
    
    nbFramesSinceRemoval = 0
    nbRemovals = 0
    nbFramesSinceRemovalList = []
    
    previousFrameNumber = FrameNumberNoInterBout[0] - 1
    for frameNumber in FrameNumberNoInterBout:
      if (frameNumber - 1) == previousFrameNumber:
        nbFramesSinceRemoval += 1
      else:
        nbFramesSinceRemovalList.append(nbFramesSinceRemoval)
        nbRemovals += 1
        nbFramesSinceRemoval = 0
      previousFrameNumber = frameNumber
    if nbFramesSinceRemoval != 0:
      nbFramesSinceRemovalList.append(nbFramesSinceRemoval)
      nbRemovals += 1
    
    print("Number of cuts:", nbRemovals-1)
    print("Mean uncut period:", np.mean(nbFramesSinceRemovalList), "; Median uncut period:", np.median(nbFramesSinceRemovalList))
    
    data_df = pd.DataFrame(np.array([nbFramesSinceRemovalList]).transpose(), columns=['A'])
    sns.boxplot(data=data_df, orient="v", color=".8")
    sns.stripplot(data=data_df, orient="v", color=".3")
    plt.show()
    
    #
    plt.plot(TailAngle0savedBeforeRemoval)
    plt.plot(FrameNumberNoInterBout, TailAngle0savedBeforeRemoval[FrameNumberNoInterBout])
    plt.show()
    
    #
    N = len(TailAngle0savedBeforeRemoval[FrameNumberNoInterBout])
    T = 1/160
    xf = fftfreq(N, T)[:N//2]
    yf0 = fft(TailAngle0savedBeforeRemoval[FrameNumberNoInterBout])
    plt.plot(xf, 2.0/N * np.abs(yf0[0:N//2]))
    plt.grid()
    plt.show()

