import matplotlib.pyplot as plt
import math

def generateAllTimeTailAngleGraph(path, superStruct, generateAllTimeTailAngleGraphLineWidth):
  
  for i in range(0, len(superStruct["wellPoissMouv"])):
    for j in range(0, len(superStruct["wellPoissMouv"][i])):
      for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
        tailAngle = superStruct["wellPoissMouv"][i][j][k]["TailAngle_smoothed"]
        plt.figure()
        tailAngle2 = [(180/math.pi)*t for t in tailAngle]
        plt.plot(tailAngle2, linewidth=generateAllTimeTailAngleGraphLineWidth)
        plt.axis([0, 1300, -38, 38])
        plt.savefig(path+'/well'+str(i)+'_bout'+str(k)+'.png', dpi=1200)
        plt.savefig(path+'/well'+str(i)+'_bout'+str(k)+'.pdf', dpi=1200)
        plt.savefig(path+'/well'+str(i)+'_bout'+str(k)+'.eps', dpi=1200)
