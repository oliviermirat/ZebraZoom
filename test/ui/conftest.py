import os
import shutil
import sys

import pytest

from zebrazoom.GUIAllPy import ZebraZoomApp
from zebrazoom.code import paths
from zebrazoom.code.GUI.GUI_InitialClasses import StartPage


@pytest.fixture(scope="session")
def monkeypatch_session(request):
  from _pytest.monkeypatch import MonkeyPatch
  mpatch = MonkeyPatch()
  yield mpatch
  mpatch.undo()


@pytest.fixture(scope="session")
def monkeypatchPaths(monkeypatch_session, tmp_path_factory):  # move all relevant folders to a temporary directory while tests are running
  rootPath = tmp_path_factory.mktemp("ZebraZoom")

  configurationFolder = rootPath / 'configuration'
  configurationFolder.mkdir()
  requiredConfigFiles = ('4wellsZebrafishLarvaeEscapeResponses.json', 'headEmbeddedZebrafishLarva.json')
  for fname in requiredConfigFiles:
    shutil.copyfile(os.path.join(paths.getRootDataFolder(), 'configuration', fname), configurationFolder / fname)

  ZZoutputFolder = rootPath / 'ZZoutput'
  ZZoutputFolder.mkdir()
  requiredResultsFolders = ('example1', 'example2', 'example3', 'standardValueFreelySwimZebrafishLarvae')
  for folder in requiredResultsFolders:
    shutil.copytree(os.path.join(paths.getRootDataFolder(), 'ZZoutput', folder), ZZoutputFolder / folder, ignore=shutil.ignore_patterns('parametersUsedForCalculation.json', '*.pkl', '*.xlsx'))
  requiredResultsFiles = ('example1.h5',)
  for filename in requiredResultsFiles:
    shutil.copyfile(os.path.join(paths.getRootDataFolder(), 'ZZoutput', filename),  ZZoutputFolder / filename)

  dataAnalysisFolder = rootPath / 'dataAnalysis'
  dataAnalysisFolder.mkdir()
  experimentOrganizationExcelFolder = dataAnalysisFolder / 'experimentOrganizationExcel'
  experimentOrganizationExcelFolder.mkdir()
  shutil.copyfile(os.path.join(paths.getRootDataFolder(), 'dataAnalysis', 'experimentOrganizationExcel', 'example.xlsx'), os.path.join(experimentOrganizationExcelFolder, 'example.xlsx'))
  (dataAnalysisFolder / 'data').mkdir()
  (dataAnalysisFolder / 'resultsClustering').mkdir()
  (dataAnalysisFolder / 'resultsKinematic').mkdir()

  monkeypatch_session.setattr(paths, "getRootDataFolder", lambda *args: rootPath)


@pytest.fixture(scope="session")
def qapp(monkeypatch_session, monkeypatchPaths):
  monkeypatch_session.setattr(ZebraZoomApp, "_wrapWidget", lambda self, page: page)
  return ZebraZoomApp(sys.argv)


@pytest.fixture(autouse=True)
def ensure_start_page(qtbot, qapp):  # this ensures we are at the start page at the beginning of each test, even if a test fails
  yield
  if not isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage):
    qapp.show_frame('StartPage')
    qapp.processEvents()
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))
