from PyQt5.QtWidgets import QApplication

import zebrazoom.code.util as util


def _getXYCoordinates(frame, text):
  back = False
  def backClicked():
    nonlocal back
    back = True
  coords = util.getPoint(frame, text, backBtnCb=backClicked, zoomable=True)
  if coords is not None and not back:
    return list(coords)
  app = QApplication.instance()
  app.window.centralWidget().layout().setCurrentIndex(0)
  app.configFileHistory[-2]()
  return None

def findWellLeft(frame):
  return _getXYCoordinates(frame, "Click on left border")

def findWellRight(frame):
  return _getXYCoordinates(frame, "Click on right border")

def findHeadCenter(frame):
  return _getXYCoordinates(frame, "Click on a head center")

def findBodyExtremity(frame):
  return _getXYCoordinates(frame, "Click on the tip of the tail of the same zebrafish")
