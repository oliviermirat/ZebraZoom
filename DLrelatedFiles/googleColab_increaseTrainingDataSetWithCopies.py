import os
import shutil

nbNewImagesToCreate = 9

directory = 'datasets/' + projectName + '/train/images/'
for filename in os.listdir(directory):
    if filename.endswith('.jpg'):
        original_image_path = os.path.join(directory, filename)
        for i in range(1, nbNewImagesToCreate + 1):
          new_image_path = os.path.join(directory, filename.replace('.jpg', '_' + str(i) + '.jpg'))
          shutil.copy(original_image_path, new_image_path)


directory = 'datasets/' + projectName + '/train/labels/'
for filename in os.listdir(directory):
    if filename.endswith('.txt'):
        original_image_path = os.path.join(directory, filename)
        for i in range(1, nbNewImagesToCreate + 1):
          new_image_path = os.path.join(directory, filename.replace('.txt', '_' + str(i) + '.txt')) 
          shutil.copy(original_image_path, new_image_path)
