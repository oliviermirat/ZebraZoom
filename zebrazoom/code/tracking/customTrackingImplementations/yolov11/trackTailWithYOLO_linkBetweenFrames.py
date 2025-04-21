from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO_getContours import trackTailWithYOLO_getContours
from scipy.optimize import linear_sum_assignment
from scipy.spatial import distance
import numpy as np

def track_fixed_objects(self, results, prev_contours, disappeared_counts, num_objects, 
                        max_disappeared=5, conf_threshold=0.25, max_distance=10):
    """
    Track a fixed number of objects using the Hungarian algorithm.
    
    Args:
        results: Detection results containing masks and confidence scores
        prev_contours: List of previous contours for each tracked object
        disappeared_counts: List tracking how many frames each object has been missing
        num_objects: Fixed number of objects to track
        max_disappeared: Maximum number of frames an object can disappear before being dropped
        conf_threshold: Confidence threshold for detection
        max_distance: Maximum distance for immediate association without considering disappeared count
    
    Returns:
        curr_contours: Updated contours for each tracked object
        disappeared_counts: Updated disappeared counts
    """
    
    masks = results[0].masks.xy
    
    # First-time initialization
    if not prev_contours:
        # Initialize tracking with up to num_objects detected objects
        if len(masks) > 0:
            # Get masks with confidence above threshold
            valid_mask_indices = [
                i for i, conf in enumerate(results[0].boxes.conf) 
                if conf > conf_threshold and i < len(masks)
            ]
            
            # Sort by confidence (highest first)
            valid_mask_indices.sort(key=lambda i: results[0].boxes.conf[i], reverse=True)
            
            # Take up to num_objects masks
            selected_indices = valid_mask_indices[:num_objects]
            
            # Create initial contours and disappeared counts
            curr_contours = trackTailWithYOLO_getContours(self, results)
            
            curr_disappeared_counts = [0] * len(curr_contours)
            
            # Pad with empty contours if we don't have enough detections
            if len(curr_contours) < num_objects:
                # Use placeholder contours for missing objects
                # A placeholder could be a small box in the center or corner of the frame
                placeholder = np.array([[0, 0], [0, 1], [1, 1], [1, 0]])
                
                for _ in range(num_objects - len(curr_contours)):
                    curr_contours.append(placeholder)
                    curr_disappeared_counts.append(max_disappeared)  # Mark as disappeared
            
            return curr_contours, curr_disappeared_counts
        else:
            # No detections, create placeholder contours
            placeholder = np.array([[0, 0], [0, 1], [1, 1], [1, 0]])
            curr_contours = [placeholder] * num_objects
            curr_disappeared_counts = [max_disappeared] * num_objects
            return curr_contours, curr_disappeared_counts
    
    # Ensure we have the right number of objects being tracked
    if len(prev_contours) != num_objects:
        # Adjust the number of contours to match num_objects
        if len(prev_contours) < num_objects:
            # Add placeholder contours
            placeholder = np.array([[0, 0], [0, 1], [1, 1], [1, 0]])
            prev_contours = prev_contours + [placeholder] * (num_objects - len(prev_contours))
        else:
            # Keep only the first num_objects contours
            prev_contours = prev_contours[:num_objects]
    
    # Ensure disappeared_counts matches prev_contours length
    if len(disappeared_counts) != len(prev_contours):
        disappeared_counts = [0] * len(prev_contours)
    
    # Initialize current contours with previous ones (in case no matches are found)
    curr_contours = prev_contours.copy()
    
    if len(masks) > 0:
        # Filter masks by confidence threshold
        valid_mask_indices = [
            i for i, conf in enumerate(results[0].boxes.conf) 
            if conf > conf_threshold and i < len(masks)
        ]
        
        if valid_mask_indices:
            valid_masks = trackTailWithYOLO_getContours(self, results)
            
            # Calculate cost matrix
            cost_matrix = np.zeros((num_objects, len(valid_masks)))
            
            for i, prev_contour in enumerate(prev_contours):
                for j, mask in enumerate(valid_masks):
                    if len(mask) > 1 and len(prev_contour) > 1:
                        d = distance.cdist(prev_contour, mask)
                        # Symmetric average of minimum distances
                        cost_matrix[i, j] = (d.min(axis=1).mean() + d.min(axis=0).mean()) / 2
                    else:
                        cost_matrix[i, j] = 1000000000000000000000000000000000000 # perhaps improve this later?
            
            # Apply Hungarian algorithm to find optimal assignment
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
            
            # Reset all disappeared counters to increment them later if not matched
            temp_disappeared = [disappeared_count + 1 for disappeared_count in disappeared_counts]
            # Update contours and reset disappeared counters for matched objects
            for row_idx, col_idx in zip(row_indices, col_indices):
                # Only consider matches where the distance is acceptable
                if cost_matrix[row_idx, col_idx] < max_distance or disappeared_counts[row_idx] >= max_disappeared // 2:
                    curr_contours[row_idx] = valid_masks[col_idx]
                    temp_disappeared[row_idx] = 0
            
            disappeared_counts = temp_disappeared
    else:
        # No detections, increment all disappeared counters
        disappeared_counts = [count + 1 for count in disappeared_counts]
    # Replace contours that have been disappeared too long with the best unmatched detections
    if len(masks) > 0:
        # Find contours that have been disappeared for too long
        long_disappeared_indices = [i for i, count in enumerate(disappeared_counts) 
                                   if count >= max_disappeared]
        
        if long_disappeared_indices:
            # Get unmatched detections with confidence above threshold
            matched_mask_indices = set([col_idx for _, col_idx in zip(row_indices, col_indices)])
            unmatched_mask_indices = [i for i in range(len(valid_masks)) 
                                      if i not in matched_mask_indices]
            
            # Sort by confidence (highest first)
            unmatched_mask_indices.sort(
                key=lambda i: valid_mask_indices[i] if i < len(valid_mask_indices) else 0, 
                reverse=True
            )
            
            # Replace disappeared contours with new detections
            for i, disappeared_idx in enumerate(long_disappeared_indices):
                if i < len(unmatched_mask_indices):
                    curr_contours[disappeared_idx] = valid_masks[unmatched_mask_indices[i]]
                    disappeared_counts[disappeared_idx] = 0
    
    return curr_contours, disappeared_counts


def update_fixed_tracking(self, results, prev_contours, disappeared_counts, num_objects, max_disappeared=5):
    """
    Main tracking function that maintains a fixed number of tracked objects.
    
    Args:
        results: Detection results containing masks and confidence scores
        prev_contours: List of previous contours for each tracked object
        disappeared_counts: List tracking how many frames each object has been missing
        num_objects: Fixed number of objects to track
        max_disappeared: Maximum number of frames an object can disappear
    
    Returns:
        updated_contours: Updated contours after tracking step (always num_objects length)
        updated_disappeared_counts: Updated disappeared counts (always num_objects length)
    """
    return track_fixed_objects(
        self, results, prev_contours, disappeared_counts, num_objects, max_disappeared
    )

