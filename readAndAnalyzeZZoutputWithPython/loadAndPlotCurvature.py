import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

data = pd.read_pickle('nameOfVideo.pkl')

numBout = 0
fps     = 300

curvature = data.loc[numBout]['curvature']

maxx = max([max(abs(np.array(t))) for t in curvature])

fig = plt.figure(1)
# 'BrBG' is the colormap chosen here, you can view other options on this page: https://matplotlib.org/3.5.1/tutorials/colors/colormaps.html (in the paragraph "Diverging")
plt.pcolor(curvature, vmin=-maxx, vmax=maxx, cmap='BrBG')

ax = fig.axes
ax[0].set_xlabel('Second')
ax[0].set_ylabel('Rostral to Caudal')

plt.xticks([i for i in range(0, len(curvature[0]), 10)], [int(100*(i/fps))/100 for i in range(0, len(curvature[0]), 10)])

plt.colorbar()
plt.show()
