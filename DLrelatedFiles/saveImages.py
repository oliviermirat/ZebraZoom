import cv2
import os

def extract_frames(video_path, output_folder, num_frames, savingFrequency):
    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Open video file
    video = cv2.VideoCapture(video_path)
    
    # Check if video opened successfully
    if not video.isOpened():
        print("Error: Could not open video.")
        return

    # Frame counter
    count = 0

    # Loop through frames of the video
    while count < num_frames:
        ret, frame = video.read()  # Read next frame
        if not ret:
            break  # Break if no more frames are available
        
        if count % int(savingFrequency) == 0:
          
          # Define the output path for each frame
          output_path = os.path.join(output_folder, f"frame_{count:04d}.png")
          
          # Save frame as a lossless PNG image
          cv2.imwrite(output_path, frame)  # PNG format preserves lossless quality
        
        count += 1

    # Release video
    video.release()
    print(f"Saved {count} frames to {output_folder}")

# Change as needed
video_path = 'videoName.mp4'  # Replace with your video path
output_folder = 'outputFolder' # Folder in which frames will be saved
savingFrequency = 100 # Will save every 100th frame
maxFrameNumber = 10000 # Will go through every frame in the video until the frame 10000
extract_frames(video_path, output_folder, maxFrameNumber, savingFrequency)
