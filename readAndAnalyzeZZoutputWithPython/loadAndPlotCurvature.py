import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_pickle('nameOfVideo.pkl')

numBout = 0

curvature = data.loc[numBout]['curvature']

fig = plt.figure(1)
plt.pcolor(curvature)

ax = fig.axes
ax[0].set_xlabel('Frame number')
ax[0].set_ylabel('Rostral to Caudal')
plt.colorbar()
plt.show()
