import os
import sys


def getRootDataFolder():
  if getattr(sys, 'frozen', False):
    installationFolder = os.path.dirname(sys.executable)
    if os.path.exists(os.path.join(installationFolder, 'Uninstall.exe')):  # installed using the installer
      from PyQt5.QtCore import QStandardPaths
      return os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation), 'ZebraZoom')
    return os.path.join(installationFolder, 'zebrazoom')  # simply extracted zip
  return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # running in a normal Python environment


def getDefaultZZoutputFolder():
  return os.path.join(getRootDataFolder(), 'ZZoutput')


def getConfigurationFolder():
  return os.path.join(getRootDataFolder(), 'configuration')


def getDataAnalysisFolder():
  return os.path.join(getRootDataFolder(), 'dataAnalysis')
