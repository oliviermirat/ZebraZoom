import math

import cv2
import numpy as np

from zebrazoom.code.deepLearningFunctions.labellingFunctions import drawWhitePointsOnInitialImages, saveImagesAndData


class _FindTailExtremityMixin:
  @staticmethod
  def __initialiseDistance2(distance, boundary):
    TotalBPts   = len(boundary)
    distance[0] = 0
    for i in range(1, TotalBPts+1):
      if (i == TotalBPts):
        Pt = boundary[0][0]
      else:
        Pt = boundary[i][0]
      AvantPt = boundary[i-1][0]
      Dx = AvantPt[0] - Pt[0]
      Dy = AvantPt[1] - Pt[1]
      if i:
        distance[i] = distance[i-1] + math.sqrt(Dx*Dx + Dy*Dy)
      else:
        distance[i] = math.sqrt(Dx*Dx + Dy*Dy)
    return [distance[TotalBPts], distance]

  @staticmethod
  def __calculateJuge(indice, distance, max):
    juge = 0
    if distance[indice] < max - distance[indice]:
      juge = (max-2*distance[indice])/max
    else:
      juge = (2*distance[indice]-max)/max
    return juge

  @staticmethod
  def __calculateJuge2(indice, distance, bord1, bord2, nb):

    dist  = 0
    dist2 = 0
    dist3 = 0
    dist4 = 0
    mindist = 10000000000

    if indice < bord1:
      dist  = distance[bord1] - distance[indice]
      dist2 = distance[indice] + (distance[nb] - distance[bord1])
    else:
      dist  = distance[indice] - distance[bord1]
      dist2 = distance[bord1] + ( distance[nb] - distance[indice] )

    if indice < bord2:
      dist3 = distance[bord2] - distance[indice]
      dist4 = distance[indice] + ( distance[nb] - distance[bord2] )
    else:
      dist3 = distance[indice] - distance[bord2]
      dist4 = distance[bord2] + ( distance[nb] - distance[indice] )

    if dist < mindist:
      mindist = dist

    if dist2 < mindist:
      mindist = dist2

    if dist3 < mindist:
      mindist = dist3

    if dist4 < mindist:
      mindist = dist4

    return mindist

  def __insideTailExtremete(self, distance, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, boundary, dst):
    TotalBPts = len(boundary)

    # This may require some adjustements in the future (maybe some value other than 25)
    dist_calculate_curv = int(TotalBPts / 25)
    if dist_calculate_curv < 3:
      dist_calculate_curv = 3

    max = 0

    AheadPtr  = 0
    BehindPtr = 0
    Ptr       = 0

    juge = 0
    x = 0
    y = 0

    for i in tailRange:
      AheadPtr = (i + dist_calculate_curv) % TotalBPts
      BehindPtr = (i + TotalBPts - dist_calculate_curv) % TotalBPts
      Ptr = i % TotalBPts
      AheadPt = boundary[AheadPtr][0]
      Pt = boundary[Ptr][0]

      BehindPt    = boundary[BehindPtr][0]
      AheadVec    = [AheadPt[0] - Pt[0],  AheadPt[1] - Pt[1]]

      BehindVec   = [Pt[0] - BehindPt[0], Pt[1] - BehindPt[1]]
      DotProdVal  = (AheadVec[0])*(BehindVec[0]) + (AheadVec[1])*(BehindVec[1])
      DotProds[i] = DotProdVal
      x = Pt[0]
      y = Pt[1]

      # Hmm... not sure about this part bellow...
      fin_boucle = tailRange[len(tailRange)-1]
      juge = self.__calculateJuge(i,distance,distance[fin_boucle-1])
      # The line above should probably be replace by the one below at some point !!!
      # juge=self.__calculateJuge2(i,distance,bord1,bord2,TotalBPts);
      # (juge > trackParameters.minDistFromTailExtremityToTailBasis)

      if x > max_droite:
        max_droite = x
        ind_droite = i
      if x < min_gauche:
        min_gauche = x
        ind_gauche = i
      if y > max_bas:
        max_bas = y
        ind_bas = i
      if (y < min_haut): # and (juge < 0.20):
        min_haut = y
        ind_haut = i

      droite = ind_droite
      gauche = ind_gauche
      haut   = ind_haut
      bas    = ind_bas

      max = distance[i]

    return [max, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut]

  def _findTailExtremete(self, rotatedContour, bodyContour, aaa, bord1b, bord2b, debug, dst, tailExtremityMaxJugeDecreaseCoeff):
    max  = 0
    max2 = 0
    TotalBPts = len(rotatedContour)
    DotProds = np.zeros(TotalBPts)
    distance = np.zeros(TotalBPts)

    for i in range(0, TotalBPts):
      distance[i] = 0

    distance2 = np.zeros(TotalBPts+1)
    for i in range(0, TotalBPts):
      distance2[i] = 0

    [d, distance2] = self.__initialiseDistance2(distance2, rotatedContour)

    max_droite = 0
    min_gauche = 5000
    max_bas    = 0
    min_haut   = 5000

    ind_droite = 0
    ind_gauche = 0
    ind_bas    = 0
    ind_haut   = 0

    x = 0
    y = 0

    bord1 = 0
    bord2 = 0
    if (bord2b < bord1b):
      bord1 = bord2b
      bord2 = bord1b
    else:
      bord1 = bord1b
      bord2 = bord2b

    Bord1 = rotatedContour[bord1][0]
    Bord2 = rotatedContour[bord2][0]

    max1 = distance2[bord2] - distance2[bord1]
    max2 = (distance2[bord1] - distance2[0])  + (distance2[len(rotatedContour)] - distance2[bord2])

    if self._hyperparameters["checkAllContourForTailExtremityDetect"] == 0:
      tailRange = []
      if (max1 > max2):
        for i in range(bord1, bord2):
          tailRange.append(i)
      else:
        for i in range(0, bord1):
          tailRange.append(i)
        for i in range(bord2, len(rotatedContour)):
          tailRange.append(i)
    else:
      tailRange = []
      for i in range(0, len(rotatedContour)):
        tailRange.append(i)

    [max2, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut] = self.__insideTailExtremete(distance2, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, rotatedContour, dst)

    MostCurvy = 100000
    CurrentCurviness = 0
    MostCurvyIndex = 0
    TailIndex = 0

    max_dist = 15000.0

    jugeDroite = self.__calculateJuge2(ind_droite,distance2,bord1,bord2,TotalBPts)
    jugeGauche = self.__calculateJuge2(ind_gauche,distance2,bord1,bord2,TotalBPts)
    jugeHaut   = self.__calculateJuge2(ind_haut,distance2,bord1,bord2,TotalBPts)
    jugeBas    = self.__calculateJuge2(ind_bas,distance2,bord1,bord2,TotalBPts)
    maxJuge    = 0.0
    if jugeDroite > jugeGauche:
      maxJuge = jugeDroite
    else:
      maxJuge = jugeGauche

    if jugeHaut > maxJuge:
      maxJuge = jugeHaut

    if jugeBas > maxJuge:
      maxJuge = jugeBas

    maxJuge = maxJuge - tailExtremityMaxJugeDecreaseCoeff * maxJuge

    if debug:
      print("MostCurvy:",MostCurvy,";maxJuge:",maxJuge)

    DotProdPtr = DotProds[ind_droite]
    if debug:
      print("Droite (red) = curv: ", DotProdPtr, " ; jugeDroite: ", jugeDroite)

    if ((DotProdPtr < MostCurvy) and (jugeDroite > maxJuge)):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_droite
      if debug:
        print("droite wins")

    DotProdPtr=DotProds[ind_gauche]
    if (debug):
      print("Gauche (blue) = curv: ", DotProdPtr, " ; jugeGauche: ", jugeGauche)

    if (( DotProdPtr < MostCurvy) and (jugeGauche > maxJuge)):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_gauche
      if (debug):
        print("gauche wins")

    DotProdPtr = DotProds[ind_haut]
    if debug:
      print("Haut (white) = curv: ", DotProdPtr, " ; jugeHaut: ", jugeHaut)

    if (( DotProdPtr < MostCurvy) and (jugeHaut > maxJuge) and self._hyperparameters["considerHighPointForTailExtremityDetect"]):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_haut
      if (debug):
        print("haut wins")

    DotProdPtr = DotProds[ind_bas]
    if debug:
      print("Bas (Purple)= curv: ", DotProdPtr, " ; jugeBas: ", jugeBas)

    if (( DotProdPtr < MostCurvy) and (jugeBas > maxJuge)):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_bas
      if (debug):
        print("bas wins")

    if debug:
      # Droite
      pt1 = bodyContour[int(ind_droite)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (255, 0, 0), -1)
      # Gauche
      pt1 = bodyContour[int(ind_gauche)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 255, 0), -1)
      # Haut
      pt1 = bodyContour[int(ind_haut)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
      # Bas
      pt1 = bodyContour[int(ind_bas)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (255, 255, 0), -1)
      if False: # The following can sometimes be useful when debugging
        for i in range(0, len(rotatedContour)):
          pt1 = rotatedContour[int(i)][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 0), -1)
      if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
        dst = dst[pt1[1]-200:len(dst), :]
      # Plotting points
      self._debugFrame(dst, title='Frame')

    # allPossibilities = [[ind_droite,DotProds[ind_droite],jugeDroite], [ind_gauche,DotProds[ind_gauche],jugeGauche], [ind_haut,DotProds[ind_haut],jugeHaut], [ind_bas,DotProds[ind_bas],jugeBas]]

    return [MostCurvyIndex, distance2]


class TailTrackingExtremityDetectMixin(_FindTailExtremityMixin):
  def __checkIfMidlineIsInBlob(self, headX, headY, pointAlongTheTail, bodyContour, dst, size, distance2, debugAdv):
    tail = self._getMidline(headX, headY, pointAlongTheTail, bodyContour, dst, size, distance2, debugAdv)

    tail2 = tail[0]
    n = len(tail2)
    allMidlinePointsInsideBlob = True
    for j in range(0, n):
      dist = cv2.pointPolygonTest(bodyContour,(float(tail2[j][0]),float(tail2[j][1])),False)
      if dist < 0:
        allMidlinePointsInsideBlob = False

    tailLength = 0
    if allMidlinePointsInsideBlob:
      for j in range(0, n-1):
        tailLength = tailLength + math.sqrt( pow(tail2[j,0]-tail2[j+1,0], 2) + pow(tail2[j,1]-tail2[j+1,1], 2) )

    return [allMidlinePointsInsideBlob, tailLength]

  def __findTheTwoSides(self, headPosition, bodyContour, dst):
    if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 1:

      lenX = len(dst[0])
      lenY = len(dst)
      originalShape = np.zeros((lenY, lenX))
      originalShape[:, :] = 0
      originalShape = originalShape.astype(np.uint8)
      cv2.fillPoly(originalShape, pts =[bodyContour], color=(255))

      # Heading calculation: first approximation
      minWhitePixel = 1000000000
      bestAngle     = 0
      nTries        = 50
      for i in range(0, nTries):
        angleOption = i * ((2 * math.pi) / nTries)
        startPoint = (int(headPosition[0]), int(headPosition[1]))
        endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
        testImage  = originalShape.copy()
        testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
        nbWhitePixels = cv2.countNonZero(testImage)
        if nbWhitePixels < minWhitePixel:
          minWhitePixel = nbWhitePixels
          bestAngle     = angleOption
      bestAngleAfterFirstStep = bestAngle

      # Heading calculation: second (and refined) approximation
      # Searching for the optimal value of iterationsForErodeImageForHeadingCalculation
      countTries = 0
      nbIterations2nbWhitePixels = {}
      if "iterationsForErodeImageForHeadingCalculation" in self._hyperparameters:
        iterationsForErodeImageForHeadingCalculation = self._hyperparameters["iterationsForErodeImageForHeadingCalculation"]
      else:
        iterationsForErodeImageForHeadingCalculation = 4
      kernel = np.ones((3, 3), np.uint8)
      nbWhitePixelsMax = 75
      while (iterationsForErodeImageForHeadingCalculation > 0) and (countTries < 50) and not(iterationsForErodeImageForHeadingCalculation in nbIterations2nbWhitePixels):
        testImage2 = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
        nbWhitePixels = cv2.countNonZero(testImage2)
        nbIterations2nbWhitePixels[iterationsForErodeImageForHeadingCalculation] = nbWhitePixels
        if nbWhitePixels < nbWhitePixelsMax:
          iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation - 1
        if nbWhitePixels >= nbWhitePixelsMax:
          iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation + 1
        countTries = countTries + 1
      best_iterations = 0
      minDist = 10000000000000
      for iterations in nbIterations2nbWhitePixels:
        nbWhitePixels = nbIterations2nbWhitePixels[iterations]
        dist = abs(nbWhitePixels - nbWhitePixelsMax)
        if dist < minDist:
          minDist = dist
          best_iterations = iterations
      iterationsForErodeImageForHeadingCalculation = best_iterations
      self._hyperparameters["iterationsForErodeImageForHeadingCalculation"] = iterationsForErodeImageForHeadingCalculation

      maxDist = -1
      for i in range(0, nTries):
        angleOption = bestAngleAfterFirstStep - (math.pi / 5) + i * ((2 * (math.pi / 5)) / nTries)

        startPoint = (int(headPosition[0]), int(headPosition[1]))
        endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
        testImage  = originalShape.copy()

        # applying dilation with the iterationsForErodeImageForHeadingCalculation value found
        testImage = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
        testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
        nbWhitePixels = cv2.countNonZero(testImage)
        if nbWhitePixels < minWhitePixel:
          minWhitePixel = nbWhitePixels
          bestAngle     = angleOption

      # Finding the 'mouth' of the fish
      unitVector = np.array([math.cos(bestAngle + math.pi), math.sin(bestAngle + math.pi)])
      factor     = 1
      headPos    = np.array(headPosition)
      testBorder = headPos + factor * unitVector
      testBorder = testBorder.astype(int)
      while (cv2.pointPolygonTest(bodyContour, (float(testBorder[0]), float(testBorder[1])), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
        factor = factor + 1
        testBorder = headPos + factor * unitVector

      # Finding the indexes of the two "border points" along the contour (these are the two points that are the closest from the 'mouth' of fish)
      xOtherBorder = testBorder[0]
      yOtherBorder = testBorder[1]
      minDist1 = 1000000000000
      minDist2 = 1000000000000
      indMin1  = 0
      indMin2  = 0
      for i in range(0, len(bodyContour)):
        Pt   = bodyContour[i][0]
        dist = math.sqrt((Pt[0] - xOtherBorder)**2 + (Pt[1] - yOtherBorder)**2)
        if (dist < minDist1):
          minDist2 = minDist1
          indMin2  = indMin1
          minDist1 = dist
          indMin1  = i
        else:
          if (dist < minDist2):
            minDist2 = dist
            indMin2  = i

      res = [indMin1, indMin2, bestAngle + math.pi]

    else:

      res = np.zeros(2)

      x = headPosition[0]
      y = headPosition[1]

      minDist = 1000000000000
      indMin  = 0
      for i in range(0, len(bodyContour)):
        Pt   = bodyContour[i][0]
        dist = math.sqrt((Pt[0] - x)**2 + (Pt[1] - y)**2)
        if (dist < minDist):
          minDist = dist
          indMin  = i

      res[0] = indMin
      PtClosest = bodyContour[indMin][0]
      headPos   = np.array(headPosition)

      unitVector = np.array([x - PtClosest[0], y - PtClosest[1]])
      unitVectorLength = math.sqrt(unitVector[0]**2 + unitVector[1]**2)
      unitVector[0] = unitVector[0] / unitVectorLength
      unitVector[1] = unitVector[1] / unitVectorLength

      factor = 1
      testBorder = headPos + factor * unitVector
      testBorder = testBorder.astype(int)
      while (cv2.pointPolygonTest(bodyContour, (float(testBorder[0]), float(testBorder[1])), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
        factor = factor + 1
        testBorder = headPos + factor * unitVector

      xOtherBorder = testBorder[0]
      yOtherBorder = testBorder[1]

      minDist = 1000000000000
      indMin2  = 0
      for i in range(0, len(bodyContour)):
        Pt   = bodyContour[i][0]
        dist = math.sqrt((Pt[0] - xOtherBorder)**2 + (Pt[1] - yOtherBorder)**2)
        if (dist < minDist):
          minDist = dist
          indMin2  = i

      res[1] = indMin2

    if False:
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
      cv2.circle(dst, (pt2[0],pt2[1]), 1, (0, 0, 255), -1)
      self._debugFrame(dst, title='Frame')

    return res

  def __findBodyContour(self, headPosition, thresh1, initialCurFrame, back, wellNumber=-1, frameNumber=-1):
    if self._hyperparameters["saveBodyMask"] and self._hyperparameters["bodyMask_addWhitePoints"]:
      [img, thresh1] = drawWhitePointsOnInitialImages(initialCurFrame, back, self._hyperparameters)

    thresh1[:,0] = 255
    thresh1[0,:] = 255
    thresh1[:, len(thresh1[0])-1] = 255
    thresh1[len(thresh1)-1, :]    = 255

    x = headPosition[0]
    y = headPosition[1]
    cx = 0
    cy = 0
    takeTheHeadClosestToTheCenter = 1
    bodyContour = 0

    if self._hyperparameters["findContourPrecision"] == "CHAIN_APPROX_SIMPLE":
      contourPrecision = cv2.CHAIN_APPROX_SIMPLE
    else: # self._hyperparameters["findContourPrecision"] == "CHAIN_APPROX_NONE"
      contourPrecision = cv2.CHAIN_APPROX_NONE

    if self._hyperparameters["recalculateForegroundImageBasedOnBodyArea"]:

      minPixel2nbBlackPixels = {}
      countTries = 0
      nbBlackPixels = 0
      nbBlackPixelsMax = int(self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] / self._hyperparameters["nbAnimalsPerWell"])
      minPixelDiffForBackExtract = int(self._hyperparameters["minPixelDiffForBackExtract"])
      if "minPixelDiffForBackExtractBody" in self._hyperparameters:
        minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractBody"]

      previousNbBlackPixels = []
      while (minPixelDiffForBackExtract > 0) and (countTries < 30) and not(minPixelDiffForBackExtract in minPixel2nbBlackPixels):
        curFrame = initialCurFrame.copy()
        putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
        curFrame[putToWhite] = 255
        ret, thresh1_b = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
        thresh1_b = 255 - thresh1_b
        bodyContour = 0
        contours, hierarchy = cv2.findContours(thresh1_b, cv2.RETR_TREE, contourPrecision)
        for contour in contours:
          dist = cv2.pointPolygonTest(contour, (float(x), float(y)), True)
          if dist >= 0:
            M = cv2.moments(contour)
            if M['m00']:
              cx = int(M['m10']/M['m00'])
              cy = int(M['m01']/M['m00'])
              bodyContour = contour
            else:
              cx = 0
              cy = 0
        if not(type(bodyContour) == int):
          nbBlackPixels = cv2.contourArea(bodyContour)
        else:
          nbBlackPixels = -100000000

        minPixel2nbBlackPixels[minPixelDiffForBackExtract] = nbBlackPixels
        if nbBlackPixels > nbBlackPixelsMax:
          minPixelDiffForBackExtract = minPixelDiffForBackExtract + 1
        if nbBlackPixels <= nbBlackPixelsMax:
          minPixelDiffForBackExtract = minPixelDiffForBackExtract - 1

        countTries = countTries + 1

        previousNbBlackPixels.append(nbBlackPixels)
        if len(previousNbBlackPixels) >= 3:
          lastThree = previousNbBlackPixels[len(previousNbBlackPixels)-3: len(previousNbBlackPixels)]
          if lastThree.count(lastThree[0]) == len(lastThree):
            countTries = 1000000

      best_minPixelDiffForBackExtract = 0
      minDist = 10000000000000
      for minPixelDiffForBackExtract in minPixel2nbBlackPixels:
        nbBlackPixels = minPixel2nbBlackPixels[minPixelDiffForBackExtract]
        dist = abs(nbBlackPixels - nbBlackPixelsMax)
        if dist < minDist:
          minDist = dist
          best_minPixelDiffForBackExtract = minPixelDiffForBackExtract

      minPixelDiffForBackExtract = best_minPixelDiffForBackExtract
      putToWhite = (curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255

      ret, thresh1 = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh1 = 255 - thresh1

      self._hyperparameters["minPixelDiffForBackExtractBody"] = minPixelDiffForBackExtract

    contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, contourPrecision)
    for contour in contours:
      area = cv2.contourArea(contour)
      if (area >= self._hyperparameters["minAreaBody"]) and (area <= self._hyperparameters["maxAreaBody"]):
        dist = cv2.pointPolygonTest(contour, (float(x), float(y)), True)
        if dist >= 0 or self._hyperparameters["saveBodyMask"]:
          M = cv2.moments(contour)
          if M['m00']:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            bodyContour = contour
          else:
            cx = 0
            cy = 0

    if type(bodyContour) != int:
      if cv2.contourArea(bodyContour) >= self._hyperparameters["maxAreaBody"]:
        bodyContour = 0

    if self._hyperparameters["saveBodyMask"]:
      saveImagesAndData(self._hyperparameters, bodyContour, initialCurFrame, wellNumber, frameNumber)

    return bodyContour

  @staticmethod
  def _rotate(boundary, aaa, bbb, angle):
    gauche = 0
    haut   = 0

    x1 = aaa + 100*math.cos(angle)
    y1 = bbb + 100*math.sin(angle)
    x2 = aaa + 100*math.cos(angle + math.pi)
    y2 = bbb + 100*math.sin(angle + math.pi)
    x = 0
    y = 0
    r = 0
    Yoo = [x1 + gauche,y1 + haut]
    Yaa = [x2 + gauche,y2 + haut]

    dist1 = 0
    min_dist1 = 1000000
    dist2 = 0
    min_dist2 = 1000000
    theta = 0
    alpha = 0
    alpha_aux = 0
    final_angle = 0
    for i in range(0, len(boundary)):
      Pt = boundary[i][0]
      dist1 = (Pt[0] - x1)*(Pt[0] - x1) + (Pt[1] - y1)*(Pt[1] - y1)
      dist2 = (Pt[0] - x2)*(Pt[0] - x2) + (Pt[1] - y2)*(Pt[1] - y2)
      if (dist1<min_dist1):
        min_dist1 = dist1
      if (dist2<min_dist2):
        min_dist2 = dist2

    if (min_dist1<min_dist2):
      theta = angle
    else:
      theta = angle + math.pi

    theta = (math.pi/2) - theta

    for i in range(0, len(boundary)):
      Pt = boundary[i][0]
      x = Pt[0]
      y = Pt[1]
      x = x - aaa
      y = y - bbb
      r = math.sqrt(x*x + y*y)
      if (x>0):
        alpha = math.atan(y/x)
      if (x<0):
        x = -x
        alpha_aux = math.atan(y/x)
        alpha = math.pi - alpha_aux
      if (x == 0):
        if (y>0):
          alpha = math.pi/2
        else:
          alpha = -math.pi/2

      final_angle = theta + alpha
      x = r*math.cos(final_angle)
      y = r*math.sin(final_angle)
      Pt[0] = x + aaa
      Pt[1] = y + bbb + 200

      boundary[i] = Pt

    return boundary

  @staticmethod
  def __resampleSeqConstPtsPerArcLength(OrigBound, numTailPoints):
    n = len(OrigBound)
    distOrg = np.zeros(n)
    xOrg    = np.zeros(n)
    yOrg    = np.zeros(n)

    totDist = 0
    distOrg[0] = totDist
    xOrg[0] = OrigBound[0][0][0]
    yOrg[0] = OrigBound[0][0][1]

    for i in range(1, n):
      diff       = math.sqrt((OrigBound[i-1][0][0]-OrigBound[i][0][0])**2 + (OrigBound[i-1][0][1]-OrigBound[i][0][1])**2)
      totDist    = totDist + diff
      distOrg[i] = totDist

    uniDist = np.zeros(numTailPoints)
    uniX    = np.zeros(numTailPoints)
    uniY    = np.zeros(numTailPoints)

    for i in range(0, numTailPoints):
      uniDist[i] = totDist * (i/(numTailPoints-1))

    for i in range(1, n):
      xOrg[i] = OrigBound[i][0][0]
      yOrg[i] = OrigBound[i][0][1]

    uniX = np.interp(uniDist, distOrg, xOrg)
    uniY = np.interp(uniDist, distOrg, yOrg)

    output = np.zeros((numTailPoints, 2))
    for i in range(0, numTailPoints):
      output[i][0] = uniX[i]
      output[i][1] = uniY[i]

    return output

  @staticmethod
  def __fillTailRanges(tailRange1,tailRange2,fillSecond,i,MostCurvyIndex):
    if (i == MostCurvyIndex):
      fillSecond = 1
    if fillSecond == 0:
      tailRange1.append(i)
    else:
      tailRange2.append(i)
    return [tailRange1,tailRange2,fillSecond]

  def _getMidline(self, bord1, bord2, MostCurvyIndex, boundary, dst, nbTailPoints, distance2, debug):
    output = np.zeros((1, 0, 2))

    minTailSize = 20
    maxTailSize = 60
    trackingPointSizeDisplay = 1

    OrigBoundA = []
    OrigBoundB = []

    if (bord2 < bord1):
      temp  = bord2
      bord2 = bord1
      bord1 = temp

    max1 = distance2[bord2] - distance2[bord1]
    max2 = (distance2[bord1] - distance2[0])  + (distance2[len(boundary)] - distance2[bord2])

    tailRangeA = []
    tailRangeB = []
    fillSecond = 0
    if (max1 > max2):
      for i in range(bord1, bord2):
        [tailRangeA,tailRangeB,fillSecond] = self.__fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
    else:
      for i in range(bord2, len(boundary)):
        [tailRangeA,tailRangeB,fillSecond] = self.__fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
      for i in range(0, bord1):
        [tailRangeA,tailRangeB,fillSecond] = self.__fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)

    OrigBoundA = boundary[tailRangeA]
    OrigBoundB = boundary[tailRangeB]

    if ((bord1!=bord2) and (bord1!=MostCurvyIndex) and (bord2!=MostCurvyIndex) and not((bord1==1) and (bord2==1) and (MostCurvyIndex==1)) and (len(OrigBoundA)>1) and (len(OrigBoundB)>1)):

      if False:
        for pt in OrigBoundA:
          cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (0, 255, 0), -1)
        for pt in OrigBoundB:
          cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (255, 0, 0), -1)
        self._debugFrame(dst, title='dst')

      NBoundA = self.__resampleSeqConstPtsPerArcLength(OrigBoundA, nbTailPoints)
      NBoundB = self.__resampleSeqConstPtsPerArcLength(OrigBoundB, nbTailPoints)

      # calculates length of the tail
      TotalDist = 0
      for i in range(1, nbTailPoints):
        Pt  = NBoundB[i % nbTailPoints]
        Pt2 = NBoundA[nbTailPoints - i]
        x = (Pt[0]+Pt2[0]) / 2
        y = (Pt[1]+Pt2[1]) / 2
        if i > 1:
          TotalDist = TotalDist + math.sqrt((x-xAvant)*(x-xAvant)+(y-yAvant)*(y-yAvant))
        xAvant = x
        yAvant = y

      if ((TotalDist<self._hyperparameters["minTailSize"]) or (TotalDist>self._hyperparameters["maxTailSize"])):

        if (debug):
          print("innapropriate tail size! TailDist: ", TotalDist, " ; but minTailSize is ", minTailSize, " and maxTailSize is ", maxTailSize)

      else:

        Tail = boundary[MostCurvyIndex][0]

        point = np.array([Tail[0], Tail[1]])
        output = np.insert(output, 0, point, axis=1)

        for i in range(1, nbTailPoints):
          Pt  = NBoundB[i % nbTailPoints]
          Pt2 = NBoundA[nbTailPoints - i]
          point = np.array([(Pt[0]+Pt2[0])/2, (Pt[1]+Pt2[1])/2])
          output = np.insert(output, 0, point, axis=1)

        i = nbTailPoints-2
        if i >= 1:
          Pt =  NBoundB[i % nbTailPoints]
          Pt2 = NBoundA[nbTailPoints-i]
          ClosestPoint = [ (Pt[0]+Pt2[0])/2 , (Pt[1]+Pt2[1])/2 ]
        else:
          ClosestPoint = [-200, -200]

    else:

      # THIS SHOULD BE IMPROVED IN THE FUTURE:
      # WE SHOULD CHECK FOR TAIL LENGHT
      # ALSO WE SHOULD DO SOMETHING BETTER THAN JUST PUTTING THE TAIL TIP FOR EACH OF THE TEN POINTS !!!
      Tail = boundary[MostCurvyIndex][0]
      point = np.array([Tail[0], Tail[1]])
      for i in range(0, nbTailPoints):
        output = np.insert(output, 0, point, axis=1)

    return output

  def _tailTrackingExtremityDetect(self, headPosition, i, thresh1, frame, debugAdv, heading, initialCurFrame, back, wellNumber=-1):
    newHeading = -1

    dst = frame.copy()
    if type(dst[0][0]) == np.uint8:
      dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2RGB)
    firstFrame = self._hyperparameters["firstFrame"]
    lastFrame = self._hyperparameters["lastFrame"]

    if self._hyperparameters["debugTrackingThreshImg"]:
      if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
        self._debugFrame(thresh1[int(headPosition[1])-200:len(thresh1), :], title='debugTrackingThreshImg')
      else:
        self._debugFrame(thresh1, title='debugTrackingThreshImg')

    # Finding blob corresponding to the body of the fish
    bodyContour = self.__findBodyContour(headPosition, thresh1, initialCurFrame, back, wellNumber, i)
    if type(bodyContour) != int:
      # Finding the two sides of the fish
      res = self.__findTheTwoSides(headPosition, bodyContour, dst)
      if len(res) == 3:
        heading = res[2]
        newHeading = res[2]
      # Finding tail extremity
      rotatedContour = bodyContour.copy()
      rotatedContour = self._rotate(rotatedContour,int(headPosition[0]),int(headPosition[1]),heading)
      [MostCurvyIndex, distance2] = self._findTailExtremete(rotatedContour, bodyContour, headPosition[0], int(res[0]), int(res[1]), debugAdv, dst, self._hyperparameters["tailExtremityMaxJugeDecreaseCoeff"])
      if debugAdv:
        if True:
          # Head Center
          cv2.circle(dst, (int(headPosition[0]),int(headPosition[1])), 3, (255, 255, 0), -1)
          # Tail basis 1
          pt1 = bodyContour[int(res[0])][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 3, (255, 0, 0), -1)
          # Tail basis 2
          pt1 = bodyContour[int(res[1])][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 3, (180, 0, 0), -1)
          # Tail extremity
          pt1 = bodyContour[int(MostCurvyIndex)][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 3, (0, 0, 255), -1)
        else:
          for pt in bodyContour:
            cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (0, 255, 0), -1)
          cv2.circle(dst, (int(headPosition[0]),int(headPosition[1])), 1, (0, 0, 255), -1)
        #
        if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
          dst = dst[int(headPosition[1])-200:len(dst), :]
        # Plotting points
        self._debugFrame(dst, title='Frame')

      # Getting Midline
      if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 0:
        tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
      else:
        tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints, distance2, debugAdv)
        tail = np.array([tail[0][1:len(tail[0])]])

      if False:
        maxDistContourToTail = -1
        for contourPt in bodyContour:
          contourPtX = contourPt[0][0]
          contourPtY = contourPt[0][1]
          minDistContourPointToTail = 1000000000000
          for tailPt in np.append(tail[0], np.array([headPosition]), axis=0):
            tailPtX = tailPt[0]
            tailPtY = tailPt[1]
            dist = math.sqrt((tailPtX - contourPtX)**2 + (tailPtY - contourPtY)**2)
            if dist < minDistContourPointToTail:
              minDistContourPointToTail = dist
          if minDistContourPointToTail > maxDistContourToTail:
            maxDistContourToTail = minDistContourPointToTail
        print("maxDistContourToTail:", maxDistContourToTail, "; tailLength:", self._hyperparameters["minTailSize"]*10)

      if False:
        for pt in bodyContour:
          cv2.circle(dst, (pt[0][0], pt[0][1]), 3, (0, 0, 255), -1)
        self._debugFrame(dst, title='Frame')

      # Optimizing midline if necessary
      midlineIsInBlobTrackingOptimization = self._hyperparameters["midlineIsInBlobTrackingOptimization"]
      if midlineIsInBlobTrackingOptimization:
        [allInside, tailLength] = self.__checkIfMidlineIsInBlob(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
        if allInside == False:
          n = len(bodyContour)
          maxTailLength = -1
          for j in range(0, n):
            [allInside, tailLength] = self.__checkIfMidlineIsInBlob(int(res[0]), int(res[1]), j, bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
            if allInside:
              if tailLength > maxTailLength:
                MostCurvyIndex = j
                maxTailLength = tailLength
          tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
      # Applying snake on tail
      applySnake = False
      if applySnake:
        tail2 = tail[0]
        n = len(tail2)
        # tail2[n-1][0] = tail2[n-1][0] + (tail2[n-1][0] - tail2[n-2][0]) * 6
        # tail2[n-1][1] = tail2[n-1][1] + (tail2[n-1][1] - tail2[n-2][1]) * 6
        # print(type(tail))
        # r = np.linspace(tail2[0][0], tail2[0][0] + (tail2[1][0]-tail2[0][0]) * 15, 9)
        # c = np.linspace(tail2[0][1], tail2[0][1] + (tail2[1][1]-tail2[0][1]) * 15, 9)
        # tail2 = np.array([r, c]).T
        # r = np.linspace(tail2[0][0], tail2[n-1][0], 9)
        # c = np.linspace(tail2[0][1], tail2[n-1][1], 9)
        # tail2 = np.array([r, c]).T
        from skimage.color import rgb2gray
        from skimage.filters import gaussian
        from skimage.segmentation import active_contour
        snake = active_contour(gaussian(frame, 3), tail2, w_edge=-1000, bc="fixed")
        # snake = active_contour(gaussian(frame, 3), tail2, w_edge=0, bc="fixed-free")
        print(snake)
        # snake = tail2
        tail[0] = snake

    else:

      tail = np.zeros((1, 0, 2))
      point = np.array([0, 0])
      for i in range(0, self._nbTailPoints):
        tail = np.insert(tail, 0, point, axis=1)
      # if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] != 0:
        # tail = np.insert(tail, 0, point, axis=1)

    # Inserting head position, smoothing tail and creating output
    # if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 0:
      # tail = np.insert(tail, 0, headPosition, axis=1)
    tail = np.insert(tail, 0, headPosition, axis=1)

    # if self._nbTailPoints != len(tail[0]):
      # print("small problem 1 in tailTrackingExtremityDetect")

    # output = np.zeros((1, len(tail[0]), 2))
    output = np.zeros((1, self._nbTailPoints, 2))

    for idx, x in enumerate(tail[0]):
      if idx < self._nbTailPoints:
        output[0][idx][0] = x[0]
        output[0][idx][1] = x[1]
      # else:
        # print("small problem 2 in tailTrackingExtremityDetect")

    return [output, newHeading]
