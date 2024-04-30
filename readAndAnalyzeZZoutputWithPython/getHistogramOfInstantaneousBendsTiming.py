import matplotlib.pyplot as plt
import numpy as np
import pickle

with open("goodTracking.pkl", 'rb') as f:
  res = pickle.load(f)

onlyFish0 = False
onlyFish1 = True

if onlyFish0 and onlyFish1:
  print("Only select one fish 0 or 1, not both")
  import pdb
  pdb.set_trace()

if onlyFish0:
  print("Only fish 0")

if onlyFish1:
  print("Only fish 1")

# Only fish 0
if onlyFish0:
  res = res[0:3]

# Only fish 1
if onlyFish1:
  res = res[3:]

instantaneousBendTimingConcatenated = []

for i in range(len(res)):
  instantaneousBendTiming = (2 * np.diff(res[i]['Bend_Timing'])) / 160
  instantaneousBendTimingConcatenated = instantaneousBendTimingConcatenated + instantaneousBendTiming.tolist()

### Instantaneous TBF plot

instantaneousTBF = 1 / np.array(instantaneousBendTimingConcatenated)

plt.hist(instantaneousTBF, bins=30, color='skyblue', edgecolor='black')
plt.xlabel('TBF (Hz)', fontsize=16)
plt.ylabel('Number of occurences', fontsize=16)
plt.title('Histogram Plot', fontsize=16)
plt.show()

### Full cycle plot

plt.hist(instantaneousBendTimingConcatenated, bins=30, color='skyblue', edgecolor='black')
plt.xlabel('1 / TBF (= Full cycle duration) in seconds', fontsize=16)
plt.ylabel('Number of occurences', fontsize=16)
plt.title('Histogram Plot', fontsize=16)
plt.show()

### Full cycle plot (without values above 0.1)

instantaneousBendTimingConcatenatedHighValuesRemoved = [value for value in instantaneousBendTimingConcatenated if value <= 0.1]
plt.hist(instantaneousBendTimingConcatenatedHighValuesRemoved, bins=50, color='skyblue', edgecolor='black')
plt.xlabel('1 / TBF (= Full cycle duration) in seconds', fontsize=16)
plt.ylabel('Number of occurences', fontsize=16)
plt.title('Histogram Plot', fontsize=16)
plt.show()

dictOfVal = {}
for val in instantaneousBendTimingConcatenated:
  if val in dictOfVal:
    dictOfVal[val] += 1
  else:
    dictOfVal[val] = 1

sorted_dict = dict(sorted(dictOfVal.items()))
print(sorted_dict)

print( ((dictOfVal[0.0375]) / sum(dictOfVal.values()))*100 , "% of values are 0.0375")
