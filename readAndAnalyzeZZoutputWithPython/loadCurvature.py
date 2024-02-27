# This is an example of how load and plot a curvature matrix stored in a pickle file

import pickle

import matplotlib.pyplot as plt

outfile = open('../zebrazoom/ZZoutput/headEmbeddedZebrafishLarva/perBoutOutput/headEmbeddedZebrafishLarva_curvatureData0_0_0.txt', 'rb')
curvature = pickle.load(outfile)

fig = plt.figure(1)
plt.pcolor(curvature)

ax = fig.axes
ax[0].set_xlabel('Rostral to Caudal')
ax[0].set_ylabel('Frame number')
plt.colorbar()
plt.show()
