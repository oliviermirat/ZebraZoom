"""
Multi-channel ("temporal") YOLO detection for yolov11basedTracking, enabled by the "yoloMultiChannelFrameOffsets"
hyperparameter, for example [-3, 3]: the image given to the network for frame n is then made of the grayscale frames
n-3, n and n+3 (one channel per frame, the current frame n always included, out of range frames replaced by the
first/last frame of the video). The network must have been trained on such images, see
DLrelatedFiles/multiChannelYOLO_createDataset.py and DLrelatedFiles/zebrazoomyolov11training_multiChannel.ipynb.

Old ultralytics versions (such as the 8.3.33 used by ZebraZoom) can't run multi-channel models through YOLO.predict,
so the preprocessing and postprocessing of the ultralytics (8.4) detection predictor are replicated here.
"""

import math

import cv2
import numpy as np
import torch

from ultralytics.engine.results import Results
from ultralytics.utils import ops
from ultralytics.utils.torch_utils import select_device

try:
  from ultralytics.utils.nms import non_max_suppression  # recent ultralytics versions
except ImportError:
  from ultralytics.utils.ops import non_max_suppression  # older ultralytics versions (such as 8.3.33)


CHECKPOINT_FRAME_OFFSETS_KEY = "zebrazoomFrameOffsets"  # added to the model file by the multi-channel training notebook


# Must stay identical to the functions of the same name in DLrelatedFiles/multiChannelYOLO_createDataset.py
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


def getModelFrameOffsets(model):
  """Channel offsets stored in the model file by the multi-channel training notebook (None for other models)."""
  checkpoint = getattr(model, "ckpt", None)
  if isinstance(checkpoint, dict) and checkpoint.get(CHECKPOINT_FRAME_OFFSETS_KEY) is not None:
    return getChannelOffsets(checkpoint[CHECKPOINT_FRAME_OFFSETS_KEY])
  return None


class MultiChannelFrameReader:
  """Used instead of the cv2.VideoCapture in the tracking loop: read() returns the same (ret, frame) as
  cv2.VideoCapture.read() and also builds the multi-channel image of that frame (self.stackedImage),
  reading ahead the future frames it needs."""

  def __init__(self, cap, channelOffsets):
    self._cap = cap
    self._channelOffsets = channelOffsets
    self._frames = {}
    self._grayscaleFrames = {}
    self._nbFramesRead = 0
    self._endOfVideoReached = False
    self._frameNum = -1
    self.stackedImage = None

  def isOpened(self):
    return self._cap.isOpened()

  def release(self):
    self._cap.release()

  def _readUntil(self, frameIndex):
    while not self._endOfVideoReached and self._nbFramesRead <= frameIndex:
      ret, frame = self._cap.read()
      if not ret:
        self._endOfVideoReached = True
      else:
        self._frames[self._nbFramesRead] = frame
        self._grayscaleFrames[self._nbFramesRead] = convertFrameToGrayscale(frame)
        self._nbFramesRead += 1

  def read(self):
    frameNum = self._frameNum + 1
    self._readUntil(frameNum + self._channelOffsets[-1])
    if frameNum >= self._nbFramesRead:
      self.stackedImage = None
      return False, None
    self._frameNum = frameNum
    # Before the end of the video is reached, all the frames needed are <= self._nbFramesRead - 1, so nothing is clamped
    stackFrameIndices = getStackFrameIndices(frameNum, self._channelOffsets, self._nbFramesRead - 1)
    self.stackedImage = np.dstack([self._grayscaleFrames[frameIndex] for frameIndex in stackFrameIndices])
    for frameIndex in [frameIndex for frameIndex in self._grayscaleFrames if frameIndex < frameNum + 1 + self._channelOffsets[0]]:
      del self._grayscaleFrames[frameIndex]
    return True, self._frames.pop(frameNum)


def _letterbox(image, newShape, stride):
  """Same as ultralytics' LetterBox(newShape, auto=True, stride=stride) used by its predictor, for any number of channels."""
  shape = image.shape[:2]
  ratio = min(newShape[0] / shape[0], newShape[1] / shape[1])
  newUnpad = max(round(shape[1] * ratio), 1), max(round(shape[0] * ratio), 1)
  dw, dh = np.mod(newShape[1] - newUnpad[0], stride) / 2, np.mod(newShape[0] - newUnpad[1], stride) / 2
  if shape[::-1] != newUnpad:
    image = cv2.resize(image, newUnpad, interpolation=cv2.INTER_LINEAR)
    if image.ndim == 2:
      image = image[..., None]
  height, width, nbChannels = image.shape
  top, bottom = round(dh - 0.1), round(dh + 0.1)
  left, right = round(dw - 0.1), round(dw + 0.1)
  paddedImage = np.full((height + top + bottom, width + left + right, nbChannels), 114, dtype=image.dtype)
  paddedImage[top:top + height, left:left + width] = image
  return paddedImage


class MultiChannelYOLOPredictor:
  """Called like an ultralytics YOLO detection model (model(image, verbose=False, conf=...)), on multi-channel images."""

  def __init__(self, model):
    network = model.model
    self.nbChannels = next(module for module in network.modules() if isinstance(module, torch.nn.Conv2d)).in_channels
    if getattr(model, "task", "detect") != "detect" or getattr(network, "end2end", False):
      raise ValueError("Multi-channel tracking (yoloMultiChannelFrameOffsets) only supports YOLO detection models with NMS (such as yolo11)")
    self._device = select_device("", verbose=False)
    network = network.to(self._device)
    if hasattr(network, "fuse"):
      network = network.fuse(verbose=False)
    self._network = network.float().eval()
    self._stride = max(int(self._network.stride.max()), 32)
    imageSize = model.overrides.get("imgsz", 640)  # training image size, as used by the ultralytics predictor
    imageSize = [imageSize, imageSize] if isinstance(imageSize, int) else list(imageSize) * (2 if len(imageSize) == 1 else 1)
    self._imageSize = [math.ceil(size / self._stride) * self._stride for size in imageSize]
    self._names = self._network.names

  def __call__(self, image, verbose=False, conf=0.25, iou=0.7, max_det=300):
    if image.shape[2] != self.nbChannels:
      raise ValueError("The model expects %d channels but the image has %d channels" % (self.nbChannels, image.shape[2]))
    networkInput = torch.from_numpy(_letterbox(image, self._imageSize, self._stride)).unsqueeze(0).to(self._device)
    networkInput = networkInput.permute(0, 3, 1, 2)
    if networkInput.shape[1] == 3:
      networkInput = networkInput.flip(1)  # ultralytics treats 3-channel images as BGR and flips them to RGB (also during training)
    networkInput = networkInput.contiguous().float().div_(255)
    with torch.inference_mode():
      predictions = self._network(networkInput)
      predictions = non_max_suppression(predictions, conf, iou, classes=None, agnostic=False, max_det=max_det, nc=0)[0]
      predictions[:, :4] = ops.scale_boxes(networkInput.shape[2:], predictions[:, :4], image.shape)
      return [Results(image, path="", names=self._names, boxes=predictions[:, :6])]


def setupMultiChannelYOLO(model, hyperparameters):
  """Returns the predictor and the channel offsets to use, after checking that they match the model."""
  if hyperparameters.get("trackTailWithYOLO"):
    raise ValueError("yoloMultiChannelFrameOffsets can't be used with trackTailWithYOLO")
  channelOffsets = getChannelOffsets(hyperparameters["yoloMultiChannelFrameOffsets"])
  modelFrameOffsets = getModelFrameOffsets(model)
  if modelFrameOffsets is not None and modelFrameOffsets != channelOffsets:
    raise ValueError("yoloMultiChannelFrameOffsets " + str(hyperparameters["yoloMultiChannelFrameOffsets"]) + " (channels: frames n" +
                     ", n".join("%+d" % offset if offset else "" for offset in channelOffsets) + ") doesn't match the frame offsets the model was trained with: " + str(modelFrameOffsets))
  predictor = MultiChannelYOLOPredictor(model)
  if predictor.nbChannels != len(channelOffsets):
    raise ValueError("The model expects %d channels but yoloMultiChannelFrameOffsets %s gives %d channels (frames %s relative to the current frame)"
                     % (predictor.nbChannels, str(hyperparameters["yoloMultiChannelFrameOffsets"]), len(channelOffsets), str(channelOffsets)))
  return predictor, channelOffsets
