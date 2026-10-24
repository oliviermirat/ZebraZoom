"""
Creates a multi-channel ("temporal") YOLO training dataset for ZebraZoom's multi-channel center of mass tracking.

Each labeled image of a Roboflow "YOLOv11" export is replaced by a multi-page TIFF image whose pages (= channels) are the
grayscale video frames n + offset, for each offset of the channel offsets (e.g. [-3, 0, 3]), n being the video frame that
was labeled. Labels (.txt files) are copied unchanged from the Roboflow export.

The labeled video frame n is NOT taken blindly from the image name: every labeled image is searched (by comparing pixel
content) through the whole video, read sequentially frame by frame exactly like ZebraZoom reads videos during tracking.
Extracting frames by "jumping" to a frame number (as some frame extraction tools do) can give frames shifted by up to
hundreds of frames on some AVI files, so the frame number in the image name can be wrong.

Frames are converted to grayscale and stacked EXACTLY like ZebraZoom does during tracking
(see zebrazoom/code/tracking/customTrackingImplementations/yolov11/multiChannelYOLO.py): both must stay in sync.

Example (frame offsets default to -3,3, i.e. channels = frames n-3, n and n+3):
  python multiChannelYOLO_createDataset.py --roboflowDataset C:/data/Cavefish-28
         --videoFolders C:/cavefish2026/oldVideos C:/cavefish2026/newVideos C:/cavefish2026/newVideos2 C:/cavefish2026/newVideos3
         --frameImagesBackupFolder C:/cavefish2026/cavefishLabelingBackupUnzipped
         --outputFolder C:/data/multiChannelDataset --zip --imageSize 640
  Other frame offsets: --frameOffsets=-2,-1,1,2 (5 channels)   (note the "=" sign, needed because the value starts with "-")
  --imageSize 640 (optional) stores the images already resized for a training with imgsz=640: same training, ~4x smaller zip.
  The matching of the labeled images to the video frames is cached in the output folder: running the script again (for
  example with other frame offsets) then only takes a few minutes.

Roboflow image names are expected to look like [videoName]_[frameNumber]_png.rf.[hash].jpg. Roboflow replaces spaces and
parentheses of the original name by "-", which is taken into account when looking for the video.
When [videoName] is "frame" (images extracted beforehand and uploaded to Roboflow without the video name), the videos
are found with --frameImagesBackupFolder: a folder containing one subfolder per video, named after the video (an
optional "-b", "-c", ... and/or ".coco" suffix is ignored), each containing (at any depth) the frame_[frameNumber]...
images coming from that video (for example unzipped Roboflow COCO exports). When the same frame number exists for
several videos, all of them are searched and the best matching one is used.
"""

import os
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
  os.environ.setdefault(variable, '1')  # videos are processed in parallel by several processes: one math thread each

import argparse
import csv
import json
import math
import random
import re
import shutil
import sys
import time
import zipfile
from multiprocessing import Pool

import cv2
import numpy as np
import yaml


VIDEO_EXTENSIONS = ('.avi', '.mp4', '.mov', '.mkv', '.wmv', '.m4v', '.mpg', '.mpeg')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')
SPLITS = ('train', 'valid', 'val', 'test')
SEARCH_WIDTH, SEARCH_HEIGHT = 160, 90  # resolution at which labeled images are searched through the videos
SEARCH_BATCH = 64  # number of video frames compared at once with all the labeled images of a video
KEEP_NAMED_FRAME_FACTOR = 2.0  # the frame number of the image name is kept unless another frame matches clearly better
KEEP_NAMED_FRAME_MARGIN = 0.01
WEAK_MATCH_CONTRAST = 0.25  # match error / median error over the video above which a match is considered doubtful
TIFF_COMPRESSION_LZW = 5


# Must stay identical to the functions of the same name in
# zebrazoom/code/tracking/customTrackingImplementations/yolov11/multiChannelYOLO.py
def getChannelOffsets(frameOffsets):
  """Channel offsets: sorted unique frame offsets, the current frame (offset 0) always included."""
  return sorted(set(int(offset) for offset in frameOffsets) | {0})


def convertFrameToGrayscale(frame):
  if frame.ndim == 2:
    return frame
  if frame.shape[2] == 4:
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
  return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def getStackFrameIndices(frameNum, channelOffsets, lastFrameIndex):
  """Frame indices of the channels of the stack of frame frameNum (out of range frames replaced by the first/last frame)."""
  return [min(max(frameNum + offset, 0), lastFrameIndex) for offset in channelOffsets]
# End of the functions that must stay identical


def parseFrameOffsets(text):
  values = [value for value in re.split(r'[\s,;\[\]]+', text) if value]
  if not values:
    raise ValueError('No frame offsets found in "%s"' % text)
  return [int(value) for value in values]


def normalizeName(name):
  """Roboflow replaces characters such as spaces and parentheses by '-' in image names."""
  return re.sub(r'[^0-9a-z_\-]', '-', name.lower())


def parseImageName(fileName):
  """Returns (videoName, frameNumber) parsed from a [videoName]_[frameNumber]_png.rf.[hash].jpg name, or None."""
  stem = os.path.splitext(os.path.basename(fileName))[0]
  match = re.match(r'^(?P<original>.+)_(?:png|jpe?g|bmp|tiff?|webp)\.rf\.[0-9A-Za-z]+$', stem, re.IGNORECASE)
  original = match.group('original') if match else stem
  match = re.match(r'^(?P<video>.+)_(?P<frame>\d+)$', original)
  if not match:
    return None
  return match.group('video'), int(match.group('frame'))


def findVideos(videoFolders):
  videosByName = {}
  for videoFolder in videoFolders:
    if not os.path.isdir(videoFolder):
      raise ValueError('Video folder not found: ' + videoFolder)
    for root, _, files in os.walk(videoFolder):
      for fileName in files:
        if fileName.lower().endswith(VIDEO_EXTENSIONS):
          videosByName.setdefault(normalizeName(os.path.splitext(fileName)[0]), []).append(os.path.abspath(os.path.join(root, fileName)))
  return videosByName


def findVideosForFolderName(folderName, videosByName):
  """Video(s) corresponding to a backup folder name, ignoring suffixes such as '-b' or '.coco'."""
  candidateName = folderName
  while True:
    if normalizeName(candidateName) in videosByName:
      return videosByName[normalizeName(candidateName)]
    strippedName = re.sub(r'(\.coco|-[a-zA-Z])$', '', candidateName)
    if strippedName == candidateName:
      return []
    candidateName = strippedName


def indexBackupFolder(backupFolder, videosByName):
  """Returns {(normalizedVideoNameInImageName, frameNumber): set of video paths} from the frame images backup folder."""
  backup = {}
  for folderName in sorted(os.listdir(backupFolder)):
    folderPath = os.path.join(backupFolder, folderName)
    if not os.path.isdir(folderPath):
      continue
    videos = findVideosForFolderName(folderName, videosByName)
    if not videos:
      print('WARNING: no video found for the frame images backup folder "%s", its images will be ignored' % folderName)
      continue
    for root, _, files in os.walk(folderPath):
      for fileName in files:
        if fileName.lower().endswith(IMAGE_EXTENSIONS):
          parsed = parseImageName(fileName)
          if parsed is not None:
            backup.setdefault((normalizeName(parsed[0]), parsed[1]), set()).update(videos)
  return backup


def indexRoboflowExport(roboflowDataset):
  images = []
  for split in SPLITS:
    imagesFolder = os.path.join(roboflowDataset, split, 'images')
    if not os.path.isdir(imagesFolder):
      continue
    for fileName in sorted(os.listdir(imagesFolder)):
      if fileName.lower().endswith(IMAGE_EXTENSIONS):
        stem = os.path.splitext(fileName)[0]
        images.append({'split': split, 'fileName': fileName, 'stem': stem,
                       'imagePath': os.path.join(imagesFolder, fileName),
                       'labelPath': os.path.join(roboflowDataset, split, 'labels', stem + '.txt'),
                       'parsedName': parseImageName(fileName)})
  if not images:
    raise ValueError('No images found in ' + roboflowDataset + ' (expected subfolders such as train/images, valid/images)')
  return images


def loadSearchImage(imagePath):
  image = cv2.imdecode(np.fromfile(imagePath, np.uint8), cv2.IMREAD_GRAYSCALE)
  if image is None:
    raise ValueError('Could not read image ' + imagePath)
  return cv2.resize(image, (SEARCH_WIDTH, SEARCH_HEIGHT), interpolation=cv2.INTER_AREA).astype(np.float64).ravel()


def searchLabeledImagesInVideo(job):
  """Pass 1: mean squared error between each labeled image and EVERY frame of the video (low resolution, sequential read)."""
  videoPath, imagePaths = job
  startTime = time.time()
  references = np.stack([loadSearchImage(imagePath) for imagePath in imagePaths])  # (nbImages, nbPixels)
  referencesSquaredNorms = np.sum(references ** 2, axis=1)
  nbPixels = references.shape[1]
  errorsBatches = []
  batch = []
  cap = cv2.VideoCapture(videoPath)
  if not cap.isOpened():
    raise ValueError('Could not open video ' + videoPath)

  def processBatch():
    frames = np.stack(batch)
    errors = (np.sum(frames ** 2, axis=1)[:, None] + referencesSquaredNorms[None, :] - 2 * frames @ references.T) / nbPixels
    errorsBatches.append(np.maximum(errors, 0).astype(np.float32))
    batch.clear()

  nbFramesRead = 0
  while True:
    ret, frame = cap.read()
    if not ret:
      break
    smallFrame = cv2.resize(convertFrameToGrayscale(frame), (SEARCH_WIDTH, SEARCH_HEIGHT), interpolation=cv2.INTER_AREA)
    batch.append(smallFrame.astype(np.float64).ravel())
    nbFramesRead += 1
    if len(batch) == SEARCH_BATCH:
      processBatch()
  if batch:
    processBatch()
  cap.release()
  if nbFramesRead == 0:
    raise ValueError('Could not read any frame of video ' + videoPath)
  errors = np.concatenate(errorsBatches).T  # (nbImages, nbFramesRead)
  return videoPath, errors, nbFramesRead, time.time() - startTime


def summarizeSearch(errors, nameFrame):
  bestFrame = int(np.argmin(errors))
  return {'bestFrame': bestFrame, 'bestError': float(errors[bestFrame]),
          'nameFrameError': float(errors[nameFrame]) if nameFrame is not None and nameFrame < len(errors) else None,
          'medianError': float(np.median(errors))}


def chooseFrame(searchResult, nameFrame):
  """The frame number of the image name is kept unless another frame of the video matches clearly better."""
  nameFrameError = searchResult['nameFrameError']
  if nameFrameError is not None and nameFrameError <= KEEP_NAMED_FRAME_FACTOR * searchResult['bestError'] + KEEP_NAMED_FRAME_MARGIN:
    return nameFrame, nameFrameError
  return searchResult['bestFrame'], searchResult['bestError']


def writeMultiPageTiff(path, pages):
  params = [cv2.IMWRITE_TIFF_COMPRESSION, TIFF_COMPRESSION_LZW]
  if hasattr(cv2, 'imencodemulti'):  # handles non ascii paths
    success, encoded = cv2.imencodemulti('.tif', pages, params)
    if success:
      encoded.tofile(path)
  else:
    success = cv2.imwritemulti(path, pages, params)
  if not success:
    raise ValueError('Could not write ' + path)


def resizeLikeUltralytics(pages, imageSize):
  """Same resizing as ultralytics' training data loader (long side to imageSize, linear interpolation), so that storing
  resized images gives exactly the same training images while making the dataset much smaller."""
  height, width = pages[0].shape
  if not imageSize or imageSize >= max(height, width):
    return pages
  ratio = imageSize / max(height, width)
  newSize = (min(math.ceil(width * ratio), imageSize), min(math.ceil(height * ratio), imageSize))
  # The whole stack is resized at once (as ultralytics does): OpenCV can round differently when resizing pages one by one
  resizedStack = cv2.resize(np.dstack(pages), newSize, interpolation=cv2.INTER_LINEAR)
  return [np.ascontiguousarray(resizedStack[:, :, channel]) for channel in range(len(pages))]


def extractStacksFromVideo(job):
  """Pass 2: reads the video sequentially and writes the multi-page TIFF stack of each labeled image."""
  videoPath, nbFramesInVideo, channelOffsets, imageSize, targets = job
  startTime = time.time()
  lastFrameIndex = nbFramesInVideo - 1
  for target in targets:
    target['stackFrames'] = getStackFrameIndices(target['frame'], channelOffsets, lastFrameIndex)
  targets.sort(key=lambda target: max(target['stackFrames']))
  nbPendingUses = {}
  for target in targets:
    for frameIndex in target['stackFrames']:
      nbPendingUses[frameIndex] = nbPendingUses.get(frameIndex, 0) + 1
  storedFrames = {}
  cap = cv2.VideoCapture(videoPath)
  frameIndex = 0
  nextTarget = 0
  results = []
  while nextTarget < len(targets):
    if frameIndex in nbPendingUses:
      ret, frame = cap.read()
      if not ret:
        raise ValueError('%s: could only read %d frames instead of %d' % (videoPath, frameIndex, nbFramesInVideo))
      storedFrames[frameIndex] = convertFrameToGrayscale(frame)
    elif not cap.grab():
      raise ValueError('%s: could only read %d frames instead of %d' % (videoPath, frameIndex, nbFramesInVideo))
    while nextTarget < len(targets) and max(targets[nextTarget]['stackFrames']) <= frameIndex:
      target = targets[nextTarget]
      pages = resizeLikeUltralytics([storedFrames[index] for index in target['stackFrames']], imageSize)
      writeMultiPageTiff(target['outputPath'], pages)
      # Full resolution check: labeled image VS current frame channel (resized to the labeled image size if needed)
      labeledImage = cv2.imdecode(np.fromfile(target['imagePath'], np.uint8), cv2.IMREAD_GRAYSCALE).astype(np.float64)
      currentFrame = storedFrames[target['frame']]
      if currentFrame.shape != labeledImage.shape:
        currentFrame = cv2.resize(currentFrame, (labeledImage.shape[1], labeledImage.shape[0]), interpolation=cv2.INTER_AREA)
      results.append((target['id'], float(np.mean((currentFrame.astype(np.float64) - labeledImage) ** 2)), pages[0].shape))
      for index in target['stackFrames']:
        nbPendingUses[index] -= 1
        if nbPendingUses[index] == 0:
          del storedFrames[index]
          del nbPendingUses[index]
      nextTarget += 1
    frameIndex += 1
  cap.release()
  return videoPath, results, time.time() - startTime


def drawLabels(image, labelPath, color):
  if os.path.exists(labelPath):
    height, width = image.shape[:2]
    with open(labelPath) as f:
      for line in f:
        values = line.split()
        if len(values) >= 5:
          xCenter, yCenter, boxWidth, boxHeight = (float(value) for value in values[1:5])
          cv2.rectangle(image, (int((xCenter - boxWidth / 2) * width), int((yCenter - boxHeight / 2) * height)),
                        (int((xCenter + boxWidth / 2) * width), int((yCenter + boxHeight / 2) * height)), color, 1)
  return image


def savePreview(image, stackPath, previewPath, channelOffsets):
  """Labeled Roboflow image | first channel | current frame channel | last channel | color composite of these three."""
  success, pages = cv2.imreadmulti(stackPath, flags=cv2.IMREAD_UNCHANGED)
  if not success:
    return
  previewWidth = 480
  height, width = pages[0].shape
  previewSize = (previewWidth, int(round(height * previewWidth / width)))
  first, current, last = pages[0], pages[channelOffsets.index(0)], pages[-1]
  panels = [cv2.cvtColor(cv2.imdecode(np.fromfile(image['imagePath'], np.uint8), cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR)]
  panels += [cv2.cvtColor(page, cv2.COLOR_GRAY2BGR) for page in (first, current, last)]
  panels.append(cv2.merge([last, current, first]))  # moving animals appear in color
  titles = ['Roboflow image', 'frame n%+d' % channelOffsets[0], 'frame n', 'frame n%+d' % channelOffsets[-1], 'blue: n%+d, red: n%+d' % (channelOffsets[-1], channelOffsets[0])]
  resized = []
  for panel, title in zip(panels, titles):
    panel = drawLabels(cv2.resize(panel, previewSize, interpolation=cv2.INTER_AREA), image['labelPath'], (0, 255, 0))
    cv2.putText(panel, title, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    resized.append(panel)
  success, encoded = cv2.imencode('.png', np.vstack([np.hstack(resized[:3]), np.hstack(resized[3:] + [np.zeros_like(resized[0])])]))
  if success:
    encoded.tofile(previewPath)


def zipFolder(folder, zipPath):
  with zipfile.ZipFile(zipPath, 'w') as zipFile:
    for root, _, files in os.walk(folder):
      for fileName in sorted(files):
        path = os.path.join(root, fileName)
        compression = zipfile.ZIP_STORED if fileName.lower().endswith(('.tif', '.tiff')) else zipfile.ZIP_DEFLATED
        zipFile.write(path, os.path.relpath(path, os.path.dirname(folder)), compress_type=compression)


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--roboflowDataset', required=True, help='Folder of the Roboflow export in "YOLOv11" format (containing data.yaml, train, valid, ...)')
  parser.add_argument('--videoFolders', required=True, nargs='+', help='Folder(s) containing the videos (subfolders are also searched)')
  parser.add_argument('--frameImagesBackupFolder', default=None, help='Folder used to find the videos of images named "frame_[frameNumber]..." (see above)')
  parser.add_argument('--outputFolder', required=True)
  parser.add_argument('--frameOffsets', default='-3,3', help='Offsets of the frames added as channels, e.g. --frameOffsets=-3,3 (default) (the current frame is always included)')
  parser.add_argument('--imageSize', type=int, default=0, help='Optional: images are stored resized (long side) to this size, e.g. 640 when training with imgsz=640 (default: original video size). '
                                                                'Gives the same training images (ultralytics resizes them the same way) in a ~4x smaller dataset, but imgsz must then not be larger')
  parser.add_argument('--workers', type=int, default=min(4, os.cpu_count() or 1), help='Number of videos processed in parallel')
  parser.add_argument('--zip', action='store_true', help='Also creates a zip file of the dataset (to upload to Google Drive)')
  parser.add_argument('--skipUnmatched', action='store_true', help='Leave out the images whose video cannot be found (or whose match is doubtful) instead of stopping')
  parser.add_argument('--nbPreviews', type=int, default=20, help='Number of preview images created to visually check the stacks')
  args = parser.parse_args()
  sys.stdout.reconfigure(line_buffering=True)

  channelOffsets = getChannelOffsets(parseFrameOffsets(args.frameOffsets))
  print('Channel frame offsets:', channelOffsets, '(%d channels)' % len(channelOffsets))

  videosByName = findVideos(args.videoFolders)
  print('%d videos found' % sum(len(paths) for paths in videosByName.values()))
  backup = indexBackupFolder(args.frameImagesBackupFolder, videosByName) if args.frameImagesBackupFolder else {}
  images = indexRoboflowExport(args.roboflowDataset)
  print('%d labeled images found in the Roboflow export' % len(images))

  # Candidate videos of each labeled image
  unmatched = []
  for imageId, image in enumerate(images):
    image['id'] = imageId
    image['candidateVideos'] = []
    if image['parsedName'] is not None:
      videoName, frameNumber = normalizeName(image['parsedName'][0]), image['parsedName'][1]
      image['candidateVideos'] = sorted(videosByName.get(videoName, backup.get((videoName, frameNumber), [])))
    if not image['candidateVideos']:
      unmatched.append(image)
  if unmatched:
    print('\nNo video found for %d images:' % len(unmatched))
    for image in unmatched:
      print('  ' + image['split'] + '/' + image['fileName'])
    if not args.skipUnmatched:
      sys.exit('Stopping: add the missing videos (or frame images backup folders), or use --skipUnmatched to leave out these images')

  os.makedirs(args.outputFolder, exist_ok=True)

  # Pass 1: search each labeled image through its candidate video(s) (results cached, so that changing the frame offsets later is fast)
  cachePath = os.path.join(args.outputFolder, 'frameMatchingCache.json')
  cache = {}
  if os.path.exists(cachePath):
    with open(cachePath) as f:
      cache = json.load(f)
  cacheKey = lambda image, videoPath: '|'.join([image['split'], image['fileName'], str(os.path.getsize(image['imagePath'])), videoPath, str(os.path.getsize(videoPath))])
  imagesToSearchPerVideo = {}
  for image in images:
    for videoPath in image['candidateVideos']:
      if cacheKey(image, videoPath) not in cache:
        imagesToSearchPerVideo.setdefault(videoPath, []).append(image)
  nbFramesPerVideo = {key.split('|')[3]: value['nbFramesRead'] for key, value in cache.items()}
  jobs = sorted(imagesToSearchPerVideo.items(), key=lambda item: -len(item[1]))
  if jobs:
    print('\nPass 1/2: searching the labeled images through %d videos (each video is read entirely)...' % len(jobs))
    startTime = time.time()
    with Pool(args.workers) as pool:
      for jobNumber, (videoPath, errors, nbFramesRead, duration) in enumerate(pool.imap_unordered(searchLabeledImagesInVideo, [(videoPath, [image['imagePath'] for image in videoImages]) for videoPath, videoImages in jobs])):
        nbFramesPerVideo[videoPath] = nbFramesRead
        for image, imageErrors in zip(imagesToSearchPerVideo[videoPath], errors):
          cache[cacheKey(image, videoPath)] = dict(summarizeSearch(imageErrors, image['parsedName'][1]), nbFramesRead=nbFramesRead)
        print('  [%d/%d] %s: %d images, %d frames read (%.0fs, total %.0fs)' % (jobNumber + 1, len(jobs), os.path.basename(videoPath), len(errors), nbFramesRead, duration, time.time() - startTime))
        with open(cachePath, 'w') as f:
          json.dump(cache, f)

  # Choice of the video and of the frame of each labeled image
  doubtful = []
  for image in images:
    if not image['candidateVideos']:
      continue
    results = [(cache[cacheKey(image, videoPath)], videoPath) for videoPath in image['candidateVideos']]
    searchResult, image['video'] = min(results, key=lambda result: result[0]['bestError'])
    image['searchResult'] = searchResult
    image['frame'], image['matchError'] = chooseFrame(searchResult, image['parsedName'][1])
    image['matchContrast'] = image['matchError'] / max(searchResult['medianError'], 1e-9)
    if image['matchContrast'] > WEAK_MATCH_CONTRAST:
      doubtful.append(image)
  shifted = [image for image in images if 'frame' in image and image['frame'] != image['parsedName'][1]]
  print('\n%d images whose frame number in the video differs from the frame number in their name:' % len(shifted))
  for image in shifted:
    print('  %-75s %s: frame %d instead of %d' % (image['fileName'], os.path.basename(image['video']), image['frame'], image['parsedName'][1]))
  if doubtful:
    print('\n%d images whose best match in the video is doubtful (they may not come from these videos):' % len(doubtful))
    for image in doubtful:
      print('  %-75s %s frame %d: match error %.3f, median error over the video %.3f' % (image['fileName'], os.path.basename(image['video']), image['frame'], image['matchError'], image['searchResult']['medianError']))
    if not args.skipUnmatched:
      sys.exit('Stopping: check these images (see the previews option), or use --skipUnmatched to leave them out')
  selectedImages = [image for image in images if 'frame' in image and image not in doubtful]

  # Pass 2: writing the multi-channel images and copying the labels
  with open(os.path.join(args.roboflowDataset, 'data.yaml')) as f:
    roboflowConfig = yaml.safe_load(f)
  datasetName = os.path.basename(os.path.normpath(args.roboflowDataset)) + '_frames' + '_'.join('%+d' % offset if offset else '0' for offset in channelOffsets) + ('_size%d' % args.imageSize if args.imageSize else '')
  datasetFolder = os.path.join(args.outputFolder, datasetName)
  if os.path.exists(datasetFolder):
    shutil.rmtree(datasetFolder)
  splits = sorted(set(image['split'] for image in selectedImages), key=SPLITS.index)
  for split in splits:
    os.makedirs(os.path.join(datasetFolder, split, 'images'))
    os.makedirs(os.path.join(datasetFolder, split, 'labels'))
  imagesPerVideo = {}
  for image in selectedImages:
    image['outputPath'] = os.path.join(datasetFolder, image['split'], 'images', image['stem'] + '.tif')
    imagesPerVideo.setdefault(image['video'], []).append(image)
    if os.path.exists(image['labelPath']):
      shutil.copyfile(image['labelPath'], os.path.join(datasetFolder, image['split'], 'labels', image['stem'] + '.txt'))
  print('\nPass 2/2: writing %d multi-channel images from %d videos...' % (len(selectedImages), len(imagesPerVideo)))
  jobs = [(videoPath, nbFramesPerVideo[videoPath], channelOffsets, args.imageSize,
           [{key: image[key] for key in ('id', 'frame', 'outputPath', 'imagePath')} for image in videoImages])
          for videoPath, videoImages in sorted(imagesPerVideo.items(), key=lambda item: -max(image['frame'] for image in item[1]))]
  startTime = time.time()
  with Pool(args.workers) as pool:
    for jobNumber, (videoPath, results, duration) in enumerate(pool.imap_unordered(extractStacksFromVideo, jobs)):
      for imageId, fullResolutionError, stackShape in results:
        images[imageId]['fullResolutionError'] = fullResolutionError
        images[imageId]['stackShape'] = stackShape
      print('  [%d/%d] %s: %d images (%.0fs, total %.0fs)' % (jobNumber + 1, len(jobs), os.path.basename(videoPath), len(results), duration, time.time() - startTime))

  dataConfig = {'train': 'train/images', 'val': ('valid' if 'valid' in splits else 'val') + '/images'}
  if 'test' in splits:
    dataConfig['test'] = 'test/images'
  dataConfig.update({'nc': roboflowConfig['nc'], 'names': roboflowConfig['names'], 'channels': len(channelOffsets), 'frameOffsets': channelOffsets})
  with open(os.path.join(datasetFolder, 'data.yaml'), 'w') as f:
    f.write('# Multi-channel dataset created by multiChannelYOLO_createDataset.py from ' + os.path.basename(os.path.normpath(args.roboflowDataset)) + '\n')
    f.write('# Channel i of each image = grayscale video frame n + frameOffsets[i] (n: labeled frame)\n')
    yaml.safe_dump(dataConfig, f, sort_keys=False, default_flow_style=None)

  reportPath = os.path.join(args.outputFolder, datasetName + '_report.csv')
  with open(reportPath, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['split', 'image', 'video', 'frameNumberInName', 'frameUsed', 'nbFramesInVideo', 'lowResolutionMatchError', 'lowResolutionMedianError', 'fullResolutionMatchError', 'status'])
    for image in images:
      if 'frame' not in image:
        writer.writerow([image['split'], image['fileName'], '', image['parsedName'][1] if image['parsedName'] else '', '', '', '', '', '', 'NO VIDEO FOUND (left out)'])
      else:
        status = 'DOUBTFUL MATCH (left out)' if image in doubtful else ('ok' if image['frame'] == image['parsedName'][1] else 'ok (frame number corrected)')
        writer.writerow([image['split'], image['fileName'], image['video'], image['parsedName'][1], image['frame'], image['searchResult']['nbFramesRead'],
                         '%.4f' % image['matchError'], '%.4f' % image['searchResult']['medianError'], '%.4f' % image['fullResolutionError'] if 'fullResolutionError' in image else '', status])

  previewsFolder = os.path.join(args.outputFolder, datasetName + '_previews')
  if os.path.exists(previewsFolder):
    shutil.rmtree(previewsFolder)
  os.makedirs(previewsFolder)
  previewImages = shifted + random.Random(0).sample(selectedImages, min(args.nbPreviews, len(selectedImages)))
  for image in previewImages:
    if image in selectedImages:
      savePreview(image, image['outputPath'], os.path.join(previewsFolder, image['stem'] + '.png'), channelOffsets)

  fullResolutionErrors = [image['fullResolutionError'] for image in selectedImages]
  print('\nDataset created in', datasetFolder)
  print('  %d multi-channel images (%s)' % (len(selectedImages), ', '.join('%s: %d' % (split, sum(image['split'] == split for image in selectedImages)) for split in splits)))
  print('  image shape (height, width, channels):', sorted(set(image['stackShape'] + (len(channelOffsets),) for image in selectedImages)))
  print('  full resolution mean squared error between the labeled images and the current frame channel: median %.2f, max %.2f'
        % (np.median(fullResolutionErrors), np.max(fullResolutionErrors)))
  print('  report:', reportPath)
  print('  previews (to check visually):', previewsFolder)
  if args.zip:
    zipPath = datasetFolder + '.zip'
    print('Creating', zipPath, '...')
    zipFolder(datasetFolder, zipPath)
    print('  %.0f MB' % (os.path.getsize(zipPath) / 1e6))


if __name__ == '__main__':
  main()
