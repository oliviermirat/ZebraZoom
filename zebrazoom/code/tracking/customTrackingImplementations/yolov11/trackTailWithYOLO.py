from ultralytics.utils.plotting import Annotator, colors
from ultralytics import YOLO
from skimage.morphology import skeletonize
from scipy.spatial import distance
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree, depth_first_order
from scipy.spatial import distance
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.calculateHeading import calculateHeading
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO_linkBetweenFrames import update_fixed_tracking
import numpy as np
import cv2


def moving_average_smoothing(points, window_size=3):
    
  # Ensure that the window size is odd to have a center element
  window_size = window_size if window_size % 2 != 0 else window_size + 1
  half_window = window_size // 2
  smoothed_points = []

  # Apply moving average smoothing
  for i in range(len(points)):
    start = max(0, i - half_window)
    end = min(len(points), i + half_window + 1)
    window = points[start:end]
    smoothed_points.append(np.mean(window, axis=0))
  
  return np.array(smoothed_points)


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


def skeletonizeContour(im0, currContour, animalNum, frameNum, returnSkeletonNoMatterWhat=0):
  
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
      # print("animalNum:", animalNum, "; frameNum:", frameNum, "; 3 endpoints:", start_point)
      start_point = tuple(start_point)
    else:
      endpoints.sort(key=lambda p: p[0], reverse=True)
      start_point = tuple(endpoints[0])
      # print("animalNum:", animalNum, "; frameNum:", frameNum, "; 2 endpoints:", start_point)
    
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
  if len(ordered_points) > 10:
    indices = np.linspace(0, len(ordered_points) - 1, 10, dtype=int)
    ordered_points = ordered_points[indices]
  
  # Reshape to the required format
  ordered_points = ordered_points.reshape(-1, 1, 2)
  
  return ordered_points


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


def trackTailWithYOLO(self, im0, results, frameNum, wellNum, prev_contours, disappeared_counts):
  
  if frameNum == max(0, self._firstFrame):
    
    curr_contours = []
    for idx in range(self._hyperparameters["nbAnimalsPerWell"]):
      curr_contours.append(results[0].masks.xy[idx] if len(results[0].masks.xy) > idx else np.array([[]]))
    
  else:
    
    if True:
      curr_contours, disappeared_counts = update_fixed_tracking(results, prev_contours, disappeared_counts, self._hyperparameters["nbAnimalsPerWell"])
      prev_contours = curr_contours
  
  if im0.ndim == 3:
    im0b = cv2.cvtColor(im0, cv2.COLOR_BGR2GRAY)
  else:
    im0b = im0
  
  smooth_factor_max = 20
  
  currContourOri = []
  
  for idxContour, currContour in enumerate(curr_contours):
    currContourOri = currContour.copy()
    smooth_factor = 3
    currContour = moving_average_smoothing(currContourOri, smooth_factor)
    skeleton_points = skeletonizeContour(im0, currContour, idxContour, frameNum)
    while smooth_factor < smooth_factor_max and len(skeleton_points) == 0:
      skeleton_points = skeletonizeContour(im0, currContour, idxContour, frameNum)
      smooth_factor += 2
      currContour = moving_average_smoothing(currContourOri, smooth_factor)
    if len(skeleton_points) == 0:
      # print("nothing good found for animal", idxContour, "at frame", frameNum)
      skeleton_points = skeletonizeContour(im0, currContour, idxContour, frameNum, 1)
    skeleton_points = invertSkeletonIfNecessaryUsingTheDarkEyes(im0b, currContour, skeleton_points)
    if len(skeleton_points):
      skeleton_points[:, 0, :][0] = 2 * skeleton_points[:, 0, :][1] - skeleton_points[:, 0, :][2]
      self._trackingHeadTailAllAnimalsList[wellNum][idxContour][frameNum-self._firstFrame][:len(skeleton_points)] = skeleton_points[:, 0, :]
      self._trackingHeadingAllAnimalsList[wellNum][idxContour][frameNum-self._firstFrame] = calculateHeading(skeleton_points[:, 0, :])
  
  debug1 = self._hyperparameters["debugTracking"]
  colorsForMask = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)] # need to add more colors for debugging if tracking more than 6 animals
  if debug1:
    annotator = Annotator(im0, line_width=2)
    for idxContour, currContour in enumerate(curr_contours):
      if len(currContour):
        annotator.seg_bbox(mask=currContour, mask_color=colorsForMask[idxContour], txt_color=annotator.get_txt_color(colorsForMask[idxContour]))
      cv2.polylines(im0, self._trackingHeadTailAllAnimalsList[wellNum][idxContour][frameNum-self._firstFrame][:], isClosed=False, color=(0, 0, 255), thickness=1)
    import zebrazoom.code.util as util
    util.showFrame(im0, title="write title here")
  
  prev_contours = curr_contours 

  return [prev_contours, disappeared_counts]
