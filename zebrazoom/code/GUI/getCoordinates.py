import zebrazoom.code.util as util


def getXYCoordinates(frame, text):
  return list(util.getPoint(frame, text))

def findWellLeft(frame):
  [x, y] = getXYCoordinates(frame, "Click on left border")
  return [x, y]

def findWellRight(frame):
  [x, y] = getXYCoordinates(frame, "Click on right border")
  return [x, y]

def findHeadCenter(frame):
  [x, y] = getXYCoordinates(frame, "Click on a head center")
  return [x, y]

def findBodyExtremity(frame):
  [x, y] = getXYCoordinates(frame, "Click on the tip of the tail of the same zebrafish")
  return [x, y]
