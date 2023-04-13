from zebrazoom.code.extractParameters import calculateTailAngle
from zebrazoom.code.extractParameters import calculateAngle
from scipy.optimize import curve_fit
import numpy as np
import math

def curvatureToXYPositions(successiveAngles, firstAngle, firstX, firstY, distance):
  l    = len(successiveAngles) + 1
  xPos = np.zeros(l)
  yPos = np.zeros(l)
  xPos[0] = firstX
  yPos[0] = firstY
  currentAngle = firstAngle
  for i in range(0, len(successiveAngles)):
    currentAngle = currentAngle + successiveAngles[i]
    xPos[i + 1]  = xPos[i] + distance * math.cos(currentAngle)
    yPos[i + 1]  = yPos[i] + distance * math.sin(currentAngle)
  return [xPos, yPos]


def sin3Combination(x, a1, a2, a3, b1, b2, b3, c1, c2, c3):
  return a1 * np.sin(a2 * (x - a3)) + b1 * np.sin(b2 * (x - b3)) + c1 * np.sin(c2 * (x - c3))

def sin2Combination(x, a1, a2, a3, b1, b2, b3):
  return a1 * np.sin(a2 * (x - a3)) + b1 * np.sin(b2 * (x - b3))

def smoothBasedOnCurvature(points, polynomialDegree):
  
  tailX = points[0]
  tailY = points[1]
  
  l = len(tailX)
  curvature = np.zeros(l-2)
  distanceC = np.zeros(l-2)
  av = 0
  firstAngle = calculateAngle(np.array([tailX[0], tailY[0]]), np.array([tailX[1], tailY[1]]))
  for ii in range(1, l-1):
    angleBef = calculateAngle(np.array([tailX[ii-1], tailY[ii-1]]), np.array([tailX[ii],   tailY[ii]]))
    angleAft = calculateAngle(np.array([tailX[ii],   tailY[ii]]),   np.array([tailX[ii+1], tailY[ii+1]]))
    curvature[ii-1] = calculateTailAngle(angleBef, angleAft)
    distanceC[ii-1] = math.sqrt((tailX[ii-1] - tailX[ii])**2 + (tailY[ii-1] - tailY[ii])**2)
  
  if False:
    x = np.linspace(0, len(curvature)-1, len(curvature))
    print("x:", x)
    print("curvature:", curvature)
    popt, pcov = curve_fit(sin2Combination, x, curvature, maxfev=2000)
    curvaturePoly = sin2Combination(np.linspace(0, len(curvature)-1, len(curvature)+1), *popt)
  else:
    x = np.linspace(0,len(curvature)-1,len(curvature))
    # curvature[0] = 0
    poly = np.polyfit(x, curvature, deg=polynomialDegree)
    curvaturePoly = np.polyval(poly, np.linspace(0, len(curvature)-1, len(curvature)+1))
    # curvaturePoly[0] = 0
  
  [xPosT, yPosT] = curvatureToXYPositions(-curvaturePoly, firstAngle, tailX[0], tailY[0], np.mean(distanceC))
  
  if False:
    import matplotlib.pyplot as plt
    
    plt.plot(curvature)
    plt.plot(curvaturePoly)
    plt.show()
    
    ax = plt.gca()
    ax.invert_yaxis()
    plt.plot(tailX, tailY)
    plt.plot(xPosT, yPosT)
    plt.show()
  
  return [xPosT, yPosT]

