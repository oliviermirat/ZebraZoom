import zebrazoom.code.tracking


class ExampleTrackingMethod(zebrazoom.code.tracking.BaseTrackingMethod):
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._wellPositions = wellPositions
    self._hyperparameters = hyperparameters

  def run(self):
    return {}


zebrazoom.code.tracking.register_tracking_method('zebrazoom.example', ExampleTrackingMethod)
