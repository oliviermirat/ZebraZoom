import os
import shutil
from PIL import Image

nbNewImagesToCreate = 3

directory_images = 'datasets/' + projectName + '/train/images/'
directory_labels = 'datasets/' + projectName + '/train/labels/'

for filename in os.listdir(directory_images):
    if filename.endswith('.jpg'):
        original_image_path = os.path.join(directory_images, filename)
        image = Image.open(original_image_path)
        width, height = image.size
        
        label_filename = filename.replace('.jpg', '.txt')
        label_path = os.path.join(directory_labels, label_filename)
        
        for i in range(1, nbNewImagesToCreate + 1):
            rotated_image = image.rotate(90 * i, expand=True)
            new_image_path = os.path.join(directory_images, filename.replace('.jpg', f'_{i}.jpg'))
            rotated_image.save(new_image_path)
            
            # Adjust labels
            new_label_path = os.path.join(directory_labels, label_filename.replace('.txt', f'_{i}.txt'))
            if os.path.exists(label_path):
                with open(label_path, 'r') as f:
                    lines = f.readlines()
                
                new_lines = []
                for line in lines:
                    parts = line.strip().split()
                    class_id, x_center, y_center, w, h = map(float, parts)
                    
                    if i == 1:  # 90 degrees clockwise
                        x_new = y_center
                        y_new = 1 - x_center
                        w_new, h_new = h, w
                    elif i == 2:  # 180 degrees
                        x_new = 1 - x_center
                        y_new = 1 - y_center
                        w_new, h_new = w, h
                    elif i == 3:  # 270 degrees clockwise
                        x_new = 1 - y_center
                        y_new = x_center
                        w_new, h_new = h, w
                    
                    new_lines.append(f"{class_id} {x_new:.6f} {y_new:.6f} {w_new:.6f} {h_new:.6f}\n")
                
                with open(new_label_path, 'w') as f:
                    f.writelines(new_lines)