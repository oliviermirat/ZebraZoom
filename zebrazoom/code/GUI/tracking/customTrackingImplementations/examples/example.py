import zebrazoom.code.tracking
from zebrazoom.code.tracking.customTrackingImplementations.examples.exampleTrackingMethod import ExampleTrackingMethod


class ExampleGUITrackingMethod(ExampleTrackingMethod):
  pass


zebrazoom.code.tracking.register_tracking_method('zebrazoom.example', ExampleGUITrackingMethod)
