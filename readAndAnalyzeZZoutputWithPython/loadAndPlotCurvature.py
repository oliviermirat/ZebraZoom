import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data = pd.read_pickle('nameOfVideo.pkl')

numBout = 0

curvature = data.loc[numBout]['curvature']

maxx = max([max(abs(np.array(t))) for t in curvature])

fig = plt.figure(1)
# 'BrBG' is the colormap chosen here, you can view other options on this page: https://matplotlib.org/3.5.1/tutorials/colors/colormaps.html (in the paragraph "Diverging")
plt.pcolor(curvature, vmin=-maxx, vmax=maxx, cmap='BrBG')

ax = fig.axes
ax[0].set_xlabel('Frame number')
ax[0].set_ylabel('Rostral to Caudal')
plt.colorbar()
plt.show()
