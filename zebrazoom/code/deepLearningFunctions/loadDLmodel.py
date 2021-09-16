import os
import numpy as np
import torch
import torch.utils.data
from PIL import Image
import time

import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

from   zebrazoom.code.deepLearningFunctions.PyTorchFunctions.engine     import train_one_epoch, evaluate
import zebrazoom.code.deepLearningFunctions.PyTorchFunctions.utils      as utils
import zebrazoom.code.deepLearningFunctions.PyTorchFunctions.transforms as T


def get_instance_segmentation_model(num_classes):

  model = torchvision.models.detection.maskrcnn_resnet50_fpn(pretrained=True)
  in_features = model.roi_heads.box_predictor.cls_score.in_features
  model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
  in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
  hidden_layer = 256
  model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)
  
  return model


def loadDLmodel(pathToSavedModel):

  num_classes = 2
  device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
  model = get_instance_segmentation_model(num_classes)
  model.to(device)
  model.load_state_dict(torch.load(pathToSavedModel, map_location=device))
  model.eval()
  
  return model

