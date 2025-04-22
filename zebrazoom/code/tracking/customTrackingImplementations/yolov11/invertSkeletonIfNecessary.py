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


def invertSkeletonIfNecessaryUsingThePast(skeleton_points_cur, skeleton_points_past, numAlreadyInvertedWithThePast):
  
  if len(skeleton_points_cur) == 0:
    return [skeleton_points_cur, 0]
  
  if numAlreadyInvertedWithThePast < 50:
    mirror_points = np.copy(skeleton_points_cur)
    mirror_points[:, 0] = skeleton_points_cur[:, 0][::-1]
    
    total_distance = np.sum(np.linalg.norm(skeleton_points_cur.reshape(-1, 2) - skeleton_points_past, axis=1))
    total_distance_mirror = np.sum(np.linalg.norm(mirror_points.reshape(-1, 2) - skeleton_points_past, axis=1))
    
    if total_distance < total_distance_mirror:
      return [skeleton_points_cur, 0]
    else:
      return [mirror_points, numAlreadyInvertedWithThePast + 1]
  
  else:
    
    return [skeleton_points_cur, 0]
