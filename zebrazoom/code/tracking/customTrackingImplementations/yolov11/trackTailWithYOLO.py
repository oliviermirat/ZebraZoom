from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO_linkBetweenFrames import update_fixed_tracking
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO_getContours import trackTailWithYOLO_getContours
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO_skeletonizeContour import skeletonizeContour
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO_invertSkeletonIfNecessary import invertSkeletonIfNecessaryUsingThePast, invertSkeletonIfNecessaryUsingTheDarkEyes
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.calculateHeading import calculateHeading
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


def trackTailWithYOLO(self, im0, results, frameNum, wellNum, prev_contours, disappeared_counts, numAlreadyInvertedWithThePast):
  
  if frameNum == max(0, self._firstFrame):
    # Getting contours for first frame to track
    curr_contours = trackTailWithYOLO_getContours(self, results)
  else:
    # For subsequent frames, getting contours and linking them to the corresponding previous contours found
    curr_contours, disappeared_counts = update_fixed_tracking(self, results, prev_contours, disappeared_counts, self._hyperparameters["nbAnimalsPerWell"])
    prev_contours = curr_contours
  
  if im0.ndim == 3:
    im0b = cv2.cvtColor(im0, cv2.COLOR_BGR2GRAY)
  else:
    im0b = im0
  
  smooth_factor_max = 20
  
  currContourOri = []
  
  for idxContour, currContour in enumerate(curr_contours):
    # Iteratively increasing smoothing of the contour until good skeleton is found
    currContourOri = currContour.copy()
    smooth_factor = 3
    currContour = moving_average_smoothing(currContourOri, smooth_factor)
    skeleton_points = skeletonizeContour(self, im0, currContour, idxContour, frameNum)
    while smooth_factor < smooth_factor_max and len(skeleton_points) == 0:
      smooth_factor += 2
      currContour = moving_average_smoothing(currContourOri, smooth_factor)
      skeleton_points = skeletonizeContour(self, im0, currContour, idxContour, frameNum)
    if len(skeleton_points) == 0:
      skeleton_points = skeletonizeContour(self, im0, currContour, idxContour, frameNum, 1)
    # Inverting skeleton point when necessary
    skeleton_points = invertSkeletonIfNecessaryUsingTheDarkEyes(im0b, currContour, skeleton_points)
    if frameNum-self._firstFrame-1 >= 0:
      skeleton_points = invertSkeletonIfNecessaryUsingThePast(self, skeleton_points, wellNum, frameNum, numAlreadyInvertedWithThePast, idxContour, self._hyperparameters.get("maxConsecutiveFramesInversion", 25))
    # Storing skeleton points into the output
    if len(skeleton_points):
      skeleton_points[:, 0, :][0] = 2 * skeleton_points[:, 0, :][1] - skeleton_points[:, 0, :][2] # Need to improve this in the future!
      self._trackingHeadTailAllAnimalsList[wellNum][idxContour][frameNum-self._firstFrame][:len(skeleton_points)] = skeleton_points[:, 0, :]
      self._trackingHeadingAllAnimalsList[wellNum][idxContour][frameNum-self._firstFrame] = calculateHeading(skeleton_points[:, 0, :])

  
  # Debugging visualization option
  debug1 = self._hyperparameters["debugTracking"]
  colorsForMask = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)] # need to add more colors for debugging if tracking more than 6 animals
  if debug1:
    annotator = Annotator(im0, line_width=2)
    for idxContour, currContour in enumerate(curr_contours):
      if len(currContour):
        annotator.seg_bbox(mask=currContour, mask_color=colorsForMask[idxContour], txt_color=annotator.get_txt_color(colorsForMask[idxContour]))
      pts = np.array(self._trackingHeadTailAllAnimalsList[wellNum][idxContour][frameNum - self._firstFrame], dtype=np.int32)
      pts = pts.reshape((-1, 1, 2))  # Required shape for cv2.polylines
      cv2.polylines(im0, [pts], isClosed=False, color=(0, 0, 255), thickness=1)
    import zebrazoom.code.util as util
    util.showFrame(im0, title="write title here")
  
  prev_contours = curr_contours 

  return [prev_contours, disappeared_counts]
