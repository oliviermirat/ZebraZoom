import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_pickle('nameOfVideo.pkl')

numBout = 0

curvature = data.loc[numBout]['curvature']

fig = plt.figure(1)
plt.pcolor(curvature)

ax = fig.axes
ax[0].set_xlabel('Rostral to Caudal')
ax[0].set_ylabel('Frame number')
plt.colorbar()
plt.show()
