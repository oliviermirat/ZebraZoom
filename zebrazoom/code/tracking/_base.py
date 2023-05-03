_TRACKING_METHODS_REGISTRY = {}


class BaseTrackingMethod:
  def __init__(self, videoPath: str, wellPositions: list, hyperparameters: dict):
    '''
    Initialize tracking method.

    Parameters:
    videoPath - full path to the video
    wellPositions - a list of dicts containing keys TopLeftX, TopLeftY, LengthX, LengthY, representing the wells selected by the user
    hyperparameters - a dict containing parameter values based on the config file
    '''
    raise NotImplementedError

  def run(self) -> dict:
    '''
    Run tracking and return output in the designated format.

    Expected output format:
     - a dict mapping well numbers to well data.
     - well data is a list of dicts, each containing information about a single bout of movement
     - bout dict must contain the following keys:
       - AnimalNumber: an integer
       - BoutStart: an integer, the frame in which the bout started
       - BoutEnd: an integer, the frame in which the bout ended
       - HeadX: a list of numbers representing the X coordinates of the center of the head, one for each frame of the bout
       - HeadY: a list of numbers representing the Y coordinates of the center of the head, one for each frame of the bout       
    - depending on the type of tracking performed, it can also contain:
       - Heading: a list of main head axis angles, one for each frame of the bout
       - TailAngleRaw: a list of tail angles (see figure 1c in the original 2013 ZebraZoom paper), one for each frame of the bout (if tail tracking is performed)
       - TailX_VideoReferential: a list in which each element corresponds to a frame, with each of those element itself being a list containing all x axis coordinates of points along the tail (if tail tracking is performed)
       - TailY_VideoReferential: a list in which each element corresponds to a frame, with each of those element itself being a list containing all y axis coordinates of points along the tail (if tail tracking is performed)
    - if eyes tracking if performed:
       - leftEyeX, leftEyeY, leftEyeAngle, leftEyeArea, rightEyeX, rightEyeY, rightEyeAngle, rightEyeArea: lists of integers corresponding to the x and y coordinates, main angle and eye area of the left and right eye for each frame of the bout
    '''
    raise NotImplementedError


def register_tracking_method(name: str, factory: BaseTrackingMethod) -> None:
  '''Register a new tracking method.'''
  _TRACKING_METHODS_REGISTRY[name] = factory


def get_default_tracking_method() -> BaseTrackingMethod:
  return _TRACKING_METHODS_REGISTRY['tracking']


def get_tracking_method(method: str) -> BaseTrackingMethod:
  return _TRACKING_METHODS_REGISTRY[method]
