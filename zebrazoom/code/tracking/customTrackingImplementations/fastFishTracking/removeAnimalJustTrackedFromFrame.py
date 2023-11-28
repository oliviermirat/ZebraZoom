import cv2

def removeAnimalJustTrackedFromFrame(self, frame, wellNumber, animalId, k):
  if "largerPixelRemoval" in self._hyperparameters and self._hyperparameters["largerPixelRemoval"]:
    frame = cv2.circle(frame.copy(), (int(self._trackingDataPerWell[wellNumber][animalId][k][0][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][0][1])), int(self._hyperparameters["maxDepth"]/3), (255, 255, 255), -1)
    for pointOnTail in range(1, len(self._trackingDataPerWell[wellNumber][animalId][k])):
      start_point = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
      end_point   = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
      if pointOnTail == 1:
        end_point   = (int(3 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0] - 2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(3 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1] - 2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
      if pointOnTail == len(self._trackingDataPerWell[wellNumber][animalId][k]) - 1:
        end_point   = (int(2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0] - self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1] - self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
      cv2.line(frame, start_point, end_point, (255, 255, 255), int(self._hyperparameters["maxDepth"]/3))
  else:
    frame = cv2.circle(frame.copy(), (int(self._wellPositions[wellNumber]['topLeftX'] + self._trackingDataPerWell[wellNumber][animalId][k][0][0]), int(self._wellPositions[wellNumber]['topLeftY'] + self._trackingDataPerWell[wellNumber][animalId][k][0][1])), int(self._hyperparameters["maxDepth"]/4), (255, 255, 255), -1)
    for pointOnTail in range(1, len(self._trackingDataPerWell[wellNumber][animalId][k])):
      start_point = (int(self._wellPositions[wellNumber]['topLeftX'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(self._wellPositions[wellNumber]['topLeftY'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
      end_point   = (int(self._wellPositions[wellNumber]['topLeftX'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(self._wellPositions[wellNumber]['topLeftY'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
      cv2.line(frame, start_point, end_point, (255, 255, 255), int(self._hyperparameters["maxDepth"]/5))
  
  return frame
