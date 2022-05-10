import os
import sys
import numpy as np

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QPlainTextEdit, QVBoxLayout

import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()


class _PopUpAlgoFollowPlainTextEdit(QPlainTextEdit):
  finished = pyqtSignal()


def _update(textedit, timer):
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    with open(os.path.join(paths.getRootDataFolder(), "trace.txt"), "r") as f:
      contents = f.read()
    textedit.setPlainText(contents)
    if "ZebraZoom Analysis finished for" in contents:
      textedit.finished.emit()


def createTraceFile(msg):
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    with open(os.path.join(paths.getRootDataFolder(), "trace.txt"), "w+") as f:
      f.write(msg)


def initialise():
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    from zebrazoom.GUIAllPy import PlainApplication
    app = PlainApplication(sys.argv)
    layout = QVBoxLayout()
    textedit = _PopUpAlgoFollowPlainTextEdit()
    textedit.setFixedSize(600, 400)
    textedit.setReadOnly(True)
    layout.addWidget(textedit)
    timer = QTimer()
    timer.setInterval(0.1)
    timer.timeout.connect(lambda: _update(textedit, timer))
    timer.start()
    util.showDialog(layout, title="Tracking in Progress", exitSignals=(textedit.finished,))
    timer.stop()


def prepend(text):
  if globalVariables["mac"] != 1 and globalVariables["lin"] != 1:
    with open(os.path.join(paths.getRootDataFolder(), "trace.txt"), "r+") as f:
      content = f.read()
      f.seek(0, 0)
      f.write(text.rstrip('\r\n') + '\n' + content)
