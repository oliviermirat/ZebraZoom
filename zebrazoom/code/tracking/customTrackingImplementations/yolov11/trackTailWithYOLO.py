from ultralytics.utils.plotting import Annotator, colors
from ultralytics import YOLO
from skimage.morphology import skeletonize
from scipy.spatial import distance
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree, depth_first_order
from scipy.spatial import distance
import numpy as np
import cv2

# def downsample_skeletonOld(skeleton_points, num_points=10):
  # if len(skeleton_points) <= num_points:
    # return skeleton_points
  # indices = np.linspace(0, len(skeleton_points) - 1, num_points, dtype=int)
  # return skeleton_points[indices]
# def skeletonizeContourOld(im0, currContour):
  # img = np.zeros((len(im0), len(im0[0])), dtype=np.uint8)
  # currContour = currContour.astype('int32')
  # cv2.drawContours(img, [currContour], -1, 255, thickness=cv2.FILLED)
  # binary = img > 0
  # skeleton = skeletonize(binary)
  # skeleton_points = np.column_stack(np.where(skeleton))
  # skeleton_points = skeleton_points[:, ::-1]
  # skeleton_mask = np.zeros_like(img)
  # skeleton_mask[skeleton_points[:, 1], skeleton_points[:, 0]] = 255 
  # skeleton_points = np.array(skeleton_points, dtype=np.int32)
  # skeleton_points = skeleton_points.reshape(-1, 1, 2)
  # skeleton_points = downsample_skeleton(skeleton_points, num_points=10)
  # return skeleton_points


def skeletonizeContour(im0, currContour):
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
  
  # If we found exactly 2 endpoints, we can trace from one to the other
  if len(endpoints) >= 2:
    # For fish, we want to go from head to tail
    # Assuming the head is the endpoint with larger x-coordinate (depends on your orientation)
    # You might need to adjust this heuristic based on your specific fish orientation
    endpoints.sort(key=lambda p: p[0], reverse=True)  # Sort by x-coordinate, descending
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
    ordered_points = skeleton_points
  
  # Downsample if needed
  if len(ordered_points) > 10:
    indices = np.linspace(0, len(ordered_points) - 1, 10, dtype=int)
    ordered_points = ordered_points[indices]
  
  # Reshape to the required format
  ordered_points = ordered_points.reshape(-1, 1, 2)
  
  return ordered_points

def downsample_skeleton(skeleton_points, num_points):
  # Extract points from the nested format
  points = skeleton_points.reshape(-1, 2)
  
  if len(points) <= num_points:
    return skeleton_points
  
  # Select evenly spaced points
  indices = np.linspace(0, len(points) - 1, num_points, dtype=int)
  downsampled = points[indices]
  
  # Reshape back to the required format
  return downsampled.reshape(-1, 1, 2)




def trackTailWithYOLO(self, im0, results, frameNum, wellNum, prevContour1, prevContour2, currContour1, currContour2, disappeared1, disappeared2):
  
  if frameNum == max(0, self._firstFrame):
    
    currContour1 = results[0].masks.xy[0] if len(results[0].masks.xy) else []
    currContour2 = results[0].masks.xy[1] if len(results[0].masks.xy) > 1 else results[0].masks.xy[0]
    
  else:
    
    if True:
      masks = results[0].masks.xy
      
      if len(masks) > 0:
        minDist1 = 10000000000000
        minDist2 = 10000000000000
        bestCandidate1 = -1
        bestCandidate2 = -1
        bestCandidate1_b = -1
        bestCandidate2_b = -1
        for curId, mask in enumerate(masks):
          if curId < 4 and results[0].boxes.conf[curId] > 0.25:
            # cur contour 1
            d  = distance.cdist(prevContour1, mask)
            fd = (d.min(axis=1).mean() + d.min(axis=0).mean()) / 2
            if fd < minDist1 and (fd < 10 or disappeared1 >= 5):
              bestCandidate1_b = bestCandidate1
              bestCandidate1   = curId
              minDist1 = fd
            # cur contour 2
            d  = distance.cdist(prevContour2, mask)
            fd = (d.min(axis=1).mean() + d.min(axis=0).mean()) / 2
            if fd < minDist2 and (fd < 10 or disappeared2 >= 5):
              bestCandidate2_b = bestCandidate2
              bestCandidate2   = curId
              minDist2 = fd
        
        if bestCandidate1 == bestCandidate2:
          if minDist1 < minDist2:
            currContour1 = masks[bestCandidate1]
            disappeared1 = 0
            if bestCandidate2_b != -1:
              currContour2 = masks[bestCandidate2_b]
              disappeared2 = 0
            else:
              currContour2 = prevContour2
              disappeared2 += 1
          else:
            if bestCandidate1_b != -1:
              currContour1 = masks[bestCandidate1_b]
              disappeared1 = 0
            else:
              currContour1 = prevContour1
              disappeared1 += 1
            currContour2 = masks[bestCandidate2]
            disappeared2 = 0
        else:
          if bestCandidate1 != -1:
            currContour1 = masks[bestCandidate1]
            disappeared1 = 0
          else:
            currContour1 = prevContour1
            disappeared1 += 1
          if bestCandidate2 != -1:
            currContour2 = masks[bestCandidate2]
            disappeared2 = 0
          else:
            currContour2 = prevContour2
            disappeared2 += 1
      
      else:
        
        currContour1 = prevContour1
        currContour2 = prevContour2
        disappeared1 += 1
        disappeared2 += 1
  
  skeleton_points = skeletonizeContour(im0, currContour1)
  self._trackingHeadTailAllAnimalsList[wellNum][0][frameNum-self._firstFrame][:len(skeleton_points)] = skeleton_points[:, 0, :]
  
  skeleton_points2 = skeletonizeContour(im0, currContour2)
  self._trackingHeadTailAllAnimalsList[wellNum][1][frameNum-self._firstFrame][:len(skeleton_points2)] = skeleton_points2[:, 0, :]
  
  debug1 = self._hyperparameters["debugTracking"]
  if debug1:
    annotator = Annotator(im0, line_width=2)
    if len(currContour1):
      annotator.seg_bbox(mask=currContour1, mask_color=(0, 255, 0), txt_color=annotator.get_txt_color((0, 255, 0)))
    if len(currContour2):
      annotator.seg_bbox(mask=currContour2, mask_color=(255, 0, 0), txt_color=annotator.get_txt_color((255, 0, 0)))
    cv2.polylines(im0, [skeleton_points], isClosed=False, color=(0, 0, 255), thickness=1)
    cv2.polylines(im0, [skeleton_points2], isClosed=False, color=(0, 0, 255), thickness=1)
    import zebrazoom.code.util as util
    util.showFrame(im0, title="write title here")
  
  # debug2 = False
  # if debug2:
    # import matplotlib.pyplot as plt
    # plt.figure(figsize=(6, 6))
    # plt.plot(skeleton_points[:, 0, 0], skeleton_points[:, 0, 1], 'bo-', label='Skeleton')
    # plt.title('Skeleton Points')
    # plt.xlabel('X')
    # plt.ylabel('Y')
    # plt.legend()
    # plt.show()
  
  prevContour1 = currContour1
  prevContour2 = currContour2

  return [prevContour1, prevContour2, currContour1, currContour2, disappeared1, disappeared2]
