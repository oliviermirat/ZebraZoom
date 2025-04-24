from zebrazoom.code.tracking.customTrackingImplementations.yolov11.calculateHeading import calculateHeading
import numpy as np
import cv2

def invertSkeletonIfNecessaryUsingTheDarkEyes(image, currContour, skeleton_points):

  if len(skeleton_points) == 0:
    return skeleton_points

  mask = np.zeros_like(image, dtype=np.uint8)
  currContour = currContour.astype(np.int32)
  cv2.fillPoly(mask, [currContour], 255)
  ys, xs = np.where(mask == 255)
  pixel_values = image[ys, xs]
  sorted_indices = np.argsort(pixel_values)
  darkest_points = list(zip(xs[sorted_indices[:10]], ys[sorted_indices[:10]]))
  darkest_points_array = np.array(darkest_points)
  mean_x = np.mean(darkest_points_array[:, 0])
  mean_y = np.mean(darkest_points_array[:, 1])
  d1 = np.sum((skeleton_points[:, 0, :][0] - np.array([mean_x, mean_y]))**2)
  dN = np.sum((skeleton_points[:, 0, :][len(skeleton_points)-1] - np.array([mean_x, mean_y]))**2)
  if dN < d1:
    mirror_points = np.copy(skeleton_points)
    mirror_points[:, 0] = skeleton_points[:, 0][::-1]
    skeleton_points = mirror_points
  return skeleton_points


def invertSkeletonIfNecessaryUsingThePast(self, skeleton_points_cur, wellNum, frameNum, numAlreadyInvertedWithThePast, idxContour, maxConsecutiveFramesInversion=20):
  
  if len(skeleton_points_cur) == 0:
    numAlreadyInvertedWithThePast[idxContour] = 0
    return skeleton_points_cur
  
  skeleton_points_past = self._trackingHeadTailAllAnimalsList[wellNum][idxContour][frameNum-self._firstFrame-1]
  
  if numAlreadyInvertedWithThePast[idxContour] < maxConsecutiveFramesInversion: # Cannot invert using the past for more than maxConsecutiveFramesInversion consecutive frames
    mirror_points = np.copy(skeleton_points_cur)
    mirror_points[:, 0] = skeleton_points_cur[:, 0][::-1]
    
    total_distance = np.sum(np.linalg.norm(skeleton_points_cur.reshape(-1, 2) - skeleton_points_past, axis=1))
    total_distance_mirror = np.sum(np.linalg.norm(mirror_points.reshape(-1, 2) - skeleton_points_past, axis=1))
    
    if total_distance < total_distance_mirror:
      numAlreadyInvertedWithThePast[idxContour] = 0
      return skeleton_points_cur
    else:
      numAlreadyInvertedWithThePast[idxContour] += 1
      return mirror_points
  
  else:
    
    # Reverting back to original if maxConsecutiveFramesInversion is reached
    backIdx = frameNum-self._firstFrame-1
    while backIdx > max(0, frameNum-self._firstFrame-maxConsecutiveFramesInversion):
      skeleton_points_past = self._trackingHeadTailAllAnimalsList[wellNum][idxContour][backIdx]
      skeleton_points_past_mirror = np.flip(skeleton_points_past, 0)
      self._trackingHeadTailAllAnimalsList[wellNum][idxContour][backIdx] = skeleton_points_past_mirror
      self._trackingHeadingAllAnimalsList[wellNum][idxContour][backIdx] = calculateHeading(self._trackingHeadTailAllAnimalsList[wellNum][idxContour][backIdx])
      backIdx -= 1
    
    numAlreadyInvertedWithThePast[idxContour] = 0
    return skeleton_points_cur
