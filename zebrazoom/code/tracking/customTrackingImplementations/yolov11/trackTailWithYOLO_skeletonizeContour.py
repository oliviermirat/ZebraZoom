from skimage.morphology import skeletonize
import numpy as np
import cv2


def farthest_point(endpoints):
  max_distance = 0
  farthest_pt = None
  
  for i, p in enumerate(endpoints):
    d1 = np.linalg.norm(p - endpoints[(i+1) % 3])
    d2 = np.linalg.norm(p - endpoints[(i+2) % 3])
    total_distance = d1 + d2
    if total_distance > max_distance:
      max_distance = total_distance
      farthest_pt = p
  
  return farthest_pt


def skeletonizeContour(self, im0, currContour, animalNum, frameNum, returnSkeletonNoMatterWhat=0):
  
  if len(currContour.astype('int32')) <= 1:
    return []
  
  # Create mask from contour
  img = np.zeros((len(im0), len(im0[0])), dtype=np.uint8)
  currContour = currContour.astype('int32')
  cv2.drawContours(img, [currContour], -1, 255, thickness=cv2.FILLED)
  
  # Skeletonize
  binary = img > 0
  skeleton = skeletonize(binary)
  skeleton_img = skeleton.astype(np.uint8) * 255
  
  # Get skeleton points
  skeleton_points = np.column_stack(np.where(skeleton))
  skeleton_points = skeleton_points[:, ::-1]  # Swap columns to get (x,y) format
  
  if len(skeleton_points) == 0:
    return np.array([], dtype=np.int32).reshape(-1, 1, 2)
  
  # Find endpoints (points with only one neighbor)
  endpoints = []
  for point in skeleton_points:
    x, y = point
    neighbors = 0
    for i in range(-1, 2):
      for j in range(-1, 2):
        if i == 0 and j == 0:
          continue
        nx, ny = x + i, y + j
        if 0 <= nx < skeleton_img.shape[1] and 0 <= ny < skeleton_img.shape[0]:
          if skeleton_img[ny, nx] > 0:
            neighbors += 1
    if neighbors == 1:
      endpoints.append(point)
  
  if len(endpoints) > 3 and not(returnSkeletonNoMatterWhat):
    return []
  
  if len(endpoints) >= 2:
    
    if len(endpoints) == 3:
      start_point = farthest_point(endpoints)
      start_point = tuple(start_point)
    else:
      endpoints.sort(key=lambda p: p[0], reverse=True)
      start_point = tuple(endpoints[0])
    
    # Trace the path from head to tail
    ordered_points = []
    current = start_point
    visited = set()
    
    while True:
      ordered_points.append(current)
      visited.add(current)
        
      # Find neighbors
      x, y = current
      neighbors = []
      for i in range(-1, 2):
        for j in range(-1, 2):
          if i == 0 and j == 0:
            continue
          nx, ny = x + i, y + j
          if 0 <= nx < skeleton_img.shape[1] and 0 <= ny < skeleton_img.shape[0]:
            if skeleton_img[ny, nx] > 0 and (nx, ny) not in visited:
              neighbors.append((nx, ny))
      
      if not neighbors:
        break
          
      # Move to the next point
      current = neighbors[0]
    
    ordered_points = np.array(ordered_points, dtype=np.int32)
  else:
    # If we couldn't find clear endpoints, fall back to simply using the skeleton points
    print(len(endpoints), "Not found for animalNum:", animalNum, " and frameNum:", frameNum)
    ordered_points = skeleton_points
  
  # Downsample if needed
  nbTailPoints = int(self._hyperparameters.get("nbTailPoints", 10))
  if len(ordered_points) > nbTailPoints or len(ordered_points) < nbTailPoints:
    indices = np.linspace(0, len(ordered_points) - 1, nbTailPoints, dtype=int)
    ordered_points = ordered_points[indices]
  
  # Reshape to the required format
  ordered_points = ordered_points.reshape(-1, 1, 2)
  
  return ordered_points