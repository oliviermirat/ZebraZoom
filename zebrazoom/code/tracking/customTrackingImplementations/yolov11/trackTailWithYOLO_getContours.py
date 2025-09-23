import numpy as np
import cv2

def trackTailWithYOLO_getContours(self, results):
  curr_contours = []
  findContoursWithXY = False
  if findContoursWithXY:
    # Use the contours provided by ultralytics (only the biggest contour is provided)
    for idx in range(self._hyperparameters["nbAnimalsPerWell"]):
      curr_contours.append(results[0].masks.xy[idx] if len(results[0].masks.xy) > idx else np.array([[]]))
  else:
    # Finds the contour from the mask image provided by ultralytics (to take into account all the contours provided by ultralytics, not just the biggest one)
    totContours = []
    if results[0].masks is not None:
      for mask in results[0].masks.data:
        mask_np = (mask.cpu().numpy() * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 1:
          # If more than one contour was detected, need to merge all the contours using OpenCv's watershed
          dist = cv2.distanceTransform(mask_np, cv2.DIST_L2, 5)
          _, sure_fg = cv2.threshold(dist, 0.5 * dist.max(), 255, 0)
          sure_fg = np.uint8(sure_fg)
          # Sure background by dilating original mask
          kernel = np.ones((3,3), np.uint8)
          sure_bg = cv2.dilate(mask_np, kernel, iterations=2)
          # Unknown region is bg - fg
          unknown = cv2.subtract(sure_bg, sure_fg)
          # Marker labelling
          _, markers = cv2.connectedComponents(sure_fg)
          # Add 1 to all labels so that sure background is 1, unknown is 0
          markers = markers + 1
          markers[unknown == 255] = 0
          # Watershed needs a 3-channel image
          mask_color = cv2.cvtColor(mask_np, cv2.COLOR_GRAY2BGR)
          markers = cv2.watershed(mask_color, markers)
          # Result: areas where markers > 1 are segmented
          # Optional: merge all non-boundary regions into a single mask
          mask_np = np.uint8(markers > 1) * 255
          contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        contours = np.vstack(contours)
        totContours.append(contours)
    
    curr_contours = [cnt.reshape(-1, 2).astype(np.float32) for cnt in totContours]
    
    scale_x = int(self._hyperparameters["videoWidth"]) / int(results[0].masks.shape[2])
    scale_y = int(self._hyperparameters["videoHeight"]) / int(results[0].masks.shape[1])
    curr_contours = [np.column_stack((contour[:, 0] * scale_x, contour[:, 1] * scale_x)) for contour in curr_contours]
  
  return curr_contours
