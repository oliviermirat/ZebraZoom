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
    - depending on the type of tracking performed, it can also contain:
       - HeadX: a list of numbers representing the X coordinates, one for each frame of the bout
       - HeadY: a list of numbers representing the Y coordinates, one for each frame of the bout
       - Heading: a list of angles, one for each frame of the bout
       - TailAngleRaw: a list of angles, one for each frame of the bout
    '''
    raise NotImplementedError


def register_tracking_method(name: str, factory: BaseTrackingMethod) -> None:
  '''Register a new tracking method.'''
  _TRACKING_METHODS_REGISTRY[name] = factory


def get_default_tracking_method() -> BaseTrackingMethod:
  return _TRACKING_METHODS_REGISTRY['tracking']


def get_tracking_method(method: str) -> BaseTrackingMethod:
  return _TRACKING_METHODS_REGISTRY[method]
