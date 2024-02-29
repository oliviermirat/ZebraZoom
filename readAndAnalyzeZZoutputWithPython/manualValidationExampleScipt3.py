import matplotlib.pyplot as plt
import pickle

with open("goodTracking.pkl", 'rb') as f:
  res = pickle.load(f)

parameters = ['Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)', 'maxTailAngleAmplitude', 'Absolute Yaw (deg)', 'Signed Yaw (deg)', 'Number of Oscillations', 'meanTBF', 'Mean TBF (Hz)', 'TBF_quotient', 'TBF_instantaneous']

for param in parameters:
  curParamTab = []
  for r in res:
    curParamTab.append(r[param])
  print(param)
  print(curParamTab)
  print("")
  plt.boxplot(curParamTab)
  # plt.xlabel('Data')
  if param == 'Bout Duration (s)' or param == 'Bout Distance (mm)' or param == 'Bout Speed (mm/s)':
    # plt.ylabel(param)
    plt.title(param[5:])
  else:
    # plt.ylabel(param[5:])
    print("yello")
    plt.title(param)
  plt.show()
