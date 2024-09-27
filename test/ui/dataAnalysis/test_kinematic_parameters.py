import itertools
import json
import math
import os
import sys
import pickle
import random
import shutil

import h5py
import numpy as np
import pandas as pd
import scipy
from pandas.testing import assert_frame_equal, assert_series_equal

import pytest

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QComboBox

from zebrazoom.code import paths
from zebrazoom.code.GUI.GUI_InitialClasses import StartPage, ViewParameters
from zebrazoom.code.GUI.dataAnalysisGUI import KinematicParametersVisualization, ChooseDataAnalysisMethod, CreateExperimentOrganizationExcel, PopulationComparison


_DEFAULT_KEYS = ['Trial_ID', 'Well_ID', 'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition',
                 'Genotype', 'videoDuration', 'Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)',
                 'Angular Velocity (deg/s)', 'Absolute Yaw (deg) (from heading vals)', 'Signed Yaw (deg) (from heading vals)',
                 'headingRangeWidth', 'percentTimeSpentSwimming', 'Bout Counts', 'Bout Rate (bouts / s)']

_EXPECTED_RESULTS = {'Trial_ID': [],
                     'Well_ID': [],
                     'Animal_ID': [],
                     'NumBout': [],
                     'BoutStart': [],
                     'BoutEnd': [],
                     'Condition': [],
                     'Genotype': [],
                     'videoDuration': [],
                     'Bout Duration (s)': [],
                     'Bout Distance (mm)': [],
                     'Bout Speed (mm/s)': [],
                     'Angular Velocity (deg/s)': [],
                     'Max TBF (Hz)': [],
                     'Mean TBF (Hz)': [],
                     'medianOfInstantaneousTBF': [],
                     'Mean TBF (Hz) (based on first 4 bends)': [],
                     'Mean TBF (Hz) (based on first 6 bends)': [],
                     'Max absolute TBA (deg.)': [],
                     'maxBendAmplitudeSigned': [],
                     'Mean absolute TBA (deg.)': [],
                     'Median absolute TBA (deg.)': [],
                     'medianBendAmplitudeSigned': [],
                     'Number of Oscillations': [],
                     'meanTBF': [],
                     'maxTailAngleAmplitude': [],
                     'Absolute Yaw (deg)': [],
                     'Signed Yaw (deg)': [],
                     'Absolute Yaw (deg) (from heading vals)': [],
                     'Signed Yaw (deg) (from heading vals)': [],
                     'headingRangeWidth': [],
                     'TBA#1 timing (s)': [],
                     'TBA#1 Amplitude (deg)': [],
                     'firstBendAmplitudeSigned': [],
                     'IBI (s)': [],
                     'xmean': [],
                     'ymean': [],
                     'binaryClass25degMaxTailAngle': [],
                     'tailAngleIntegralSigned': [],
                     'BoutFrameNumberStart': [],
                     'tailAngleSymmetry': [],
                     'secondBendAmpDividedByFirst': [],
                     'tailAngleIntegral': [],
                     'maxInstantaneousSpeed': [],
                     'percentTimeSpentSwimming': [],
                     'Bout Counts': [],
                     'Bout Rate (bouts / s)': [],}
_MEDIAN_ONLY_KEYS = {'percentTimeSpentSwimming', 'Bout Counts', 'Bout Rate (bouts / s)'}
_FIRST_BOUT_REMOVED_RESULTS = {key: [] for key in _MEDIAN_ONLY_KEYS}
_ALL_ONLY_KEYS = {'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd'}

_VIDEO_NAMES = ['test%d' % idx for idx in range(1, 7)]
_VIDEO_NAMES[0] = f'{_VIDEO_NAMES[0]}.h5'
_WELLS_PER_VIDEO = []
_CONDITIONS = []
_CONDITIONS_LIST = []
_GENOTYPES = []
_GENOTYPES_LIST = []
_FPS = []
_PIXEL_SIZES = []


def _generateWave(amplitudes, duration):
  angles = []
  for amplitude in amplitudes:
    interval = random.randint(1, duration // 10)
    steps = [x * (amplitude // (interval + 1)) for x in range(1, interval + 1)]
    angles.extend([0, *steps, amplitude, *steps[::-1], 0, *map(lambda x: -x, steps), -amplitude, *map(lambda x: -x, steps[::-1])])
  for angle in itertools.islice(itertools.cycle(angles), duration):
    yield math.radians(angle)


def _generateResults():
  random.seed(777)
  resultsList = []
  for videoIdx, video in enumerate(_VIDEO_NAMES):
    numberOfWells = random.randint(10, 20) if videoIdx < 2 else random.randint(1, 5)  # generate a few large ones just to test it, but make sure tests don't run for too long
    _WELLS_PER_VIDEO.append(numberOfWells)
    conditions = ['condition%d' % random.randint(1, 4) for _ in range(numberOfWells)]
    _CONDITIONS_LIST.append(conditions)
    genotypes = ['genotype%d' % random.randint(1, 4) for _ in range(numberOfWells)]
    _GENOTYPES_LIST.append(genotypes)
    _CONDITIONS.append('[%s]' % ', '.join(conditions))
    _GENOTYPES.append('[%s]' % ', '.join(genotypes))
    firstFrame = random.randint(0, 500)
    lastFrame = random.randint(firstFrame + 1000, 10000)
    wellPoissMouv = []
    fps = random.randint(1, 500)
    _FPS.append(fps)
    pixelSize = random.randint(1, 500)
    _PIXEL_SIZES.append(pixelSize)
    results = {'firstFrame': firstFrame, 'lastFrame': lastFrame}
    results['wellPositions'] = [{'topLeftX': idx * 550, 'topLeftY': idx * 550, 'lengthX': 500, 'lengthY': 500} for idx in range(numberOfWells)]
    for wellIdx in range(numberOfWells):
      numberOfBouts = random.randint(1, 7)
      boutStartFrames = set()
      for _ in range(numberOfBouts):
        frame = random.randint(firstFrame, lastFrame - 25)
        while boutStartFrames & set(range(frame - 25, frame + 25)):
          frame = random.randint(firstFrame, lastFrame - 25)
        boutStartFrames.add(frame)
      boutStartFrames = sorted(boutStartFrames)
      boutDurations = [random.randint(20 if len(boutStartFrames) > 1 else 70, (boutStartFrames[idx+1] if idx + 1 < len(boutStartFrames) else lastFrame) - frame - 3) for idx, frame in enumerate(boutStartFrames)]
      wellBouts = []
      for boutIdx, (startFrame, duration) in enumerate(zip(boutStartFrames, boutDurations)):
        amplitudes = [random.choice([1, -1]) * random.randint(10, 80) for _ in range(3)]
        angles = list(_generateWave(amplitudes, duration))
        xMove = random.randint(1, 5)
        yMove = random.randint(1, 5)
        headX = [xMove * frame for frame in range(duration)]
        headY = [yMove * frame for frame in range(duration)]
        headX[1] = xMove * 3
        headY[1] = yMove * 3
        bendAmplitudes = []
        bendTimings = []
        radiansAmplitudes = set(map(math.radians, amplitudes))
        for idx, angle in enumerate(angles):
          if angle in radiansAmplitudes or -angle in radiansAmplitudes:
            bendAmplitudes.append(angle)
            bendTimings.append(idx)
        instantaneousTBF =  [fps / (2 * bendTimings[0])] + [fps / (2 * diff) for diff in map(lambda x, y: y - x, bendTimings, bendTimings[1:])]
        bout = {'AnimalNumber': 0,
                'BoutStart': startFrame,
                'BoutEnd': startFrame + duration - 1,
                'TailAngle_Raw': angles,
                'TailAngle_smoothed': angles,
                'TailX_VideoReferential': [[x] + [x * 0 for a in range(8)] for x in headX],
                'TailY_VideoReferential': [[y] + [y * 0 for a in range(8)] for y in headY],
                'HeadX': headX,
                'HeadY': headY,
                'Bend_Amplitude': bendAmplitudes,
                'Bend_Timing': bendTimings,
                'Heading': [0] * duration}
        wellBouts.append(bout)
        degreeBendAmplitudes = list(map(math.degrees, bendAmplitudes))
        _EXPECTED_RESULTS['Trial_ID'].append(video)
        _EXPECTED_RESULTS['Well_ID'].append(wellIdx)
        _EXPECTED_RESULTS['Animal_ID'].append(0)
        _EXPECTED_RESULTS['Condition'].append(conditions[wellIdx])
        _EXPECTED_RESULTS['Genotype'].append(genotypes[wellIdx])
        _EXPECTED_RESULTS['videoDuration'].append((lastFrame - firstFrame) / fps)
        _EXPECTED_RESULTS['NumBout'].append(boutIdx)
        _EXPECTED_RESULTS['BoutStart'].append(startFrame)
        _EXPECTED_RESULTS['BoutEnd'].append(startFrame + duration - 1)
        _EXPECTED_RESULTS['Bout Duration (s)'].append(duration / fps)
        _EXPECTED_RESULTS['Bout Distance (mm)'].append(math.sqrt(xMove * xMove + yMove * yMove) * pixelSize * (duration - 1))
        _EXPECTED_RESULTS['maxInstantaneousSpeed'].append(math.sqrt(xMove * xMove + yMove * yMove) * 3 * pixelSize * fps)
        _EXPECTED_RESULTS['Bout Speed (mm/s)'].append(math.sqrt(xMove * xMove + yMove * yMove) * pixelSize * fps)
        _EXPECTED_RESULTS['Angular Velocity (deg/s)'].append(0) # XXX: modify test data to include non-zero angular velocity?
        _EXPECTED_RESULTS['Max TBF (Hz)'].append(max(instantaneousTBF))
        _EXPECTED_RESULTS['Mean TBF (Hz)'].append(np.mean(instantaneousTBF))
        _EXPECTED_RESULTS['medianOfInstantaneousTBF'].append(np.median(instantaneousTBF))
        _EXPECTED_RESULTS['Mean TBF (Hz) (based on first 4 bends)'].append(np.mean(instantaneousTBF[:4]))
        _EXPECTED_RESULTS['Mean TBF (Hz) (based on first 6 bends)'].append(np.mean(instantaneousTBF[:6]))
        _EXPECTED_RESULTS['Max absolute TBA (deg.)'].append(max(map(abs, degreeBendAmplitudes)))
        _EXPECTED_RESULTS['maxBendAmplitudeSigned'].append(max(degreeBendAmplitudes, key=abs))
        _EXPECTED_RESULTS['Mean absolute TBA (deg.)'].append(np.mean(list(map(abs, degreeBendAmplitudes))))
        _EXPECTED_RESULTS['Median absolute TBA (deg.)'].append(np.median(list(map(abs, degreeBendAmplitudes))))
        _EXPECTED_RESULTS['medianBendAmplitudeSigned'].append(np.median(degreeBendAmplitudes))
        _EXPECTED_RESULTS['Number of Oscillations'].append(len(degreeBendAmplitudes) / 2)
        _EXPECTED_RESULTS['meanTBF'].append((len(degreeBendAmplitudes) * fps)  / (2 * duration))
        _EXPECTED_RESULTS['maxTailAngleAmplitude'].append(max(map(lambda x: math.degrees(abs(x)), angles)))
        _EXPECTED_RESULTS['Absolute Yaw (deg)'].append(math.degrees(math.atan(yMove / xMove)))
        _EXPECTED_RESULTS['Signed Yaw (deg)'].append(math.degrees(math.atan(yMove / xMove)))
        _EXPECTED_RESULTS['Absolute Yaw (deg) (from heading vals)'].append(0) # XXX: modify test data to include non-zero yaw? currently covered by TestExampleExperiment
        _EXPECTED_RESULTS['Signed Yaw (deg) (from heading vals)'].append(0) # XXX: modify test data to include non-zero yaw? currently covered by TestExampleExperiment
        _EXPECTED_RESULTS['headingRangeWidth'].append(0) # XXX: modify test data to include non-zero yaw? currently covered by TestExampleExperiment
        _EXPECTED_RESULTS['TBA#1 timing (s)'].append(bendTimings[0] / fps)
        _EXPECTED_RESULTS['TBA#1 Amplitude (deg)'].append(abs(degreeBendAmplitudes[0]))
        _EXPECTED_RESULTS['firstBendAmplitudeSigned'].append(degreeBendAmplitudes[0])
        _EXPECTED_RESULTS['IBI (s)'].append((startFrame - (boutStartFrames[boutIdx-1] + boutDurations[boutIdx-1] - 1 if boutIdx else 0)) / fps)
        _EXPECTED_RESULTS['xmean'].append(sum(headX) * pixelSize / len(headX))
        _EXPECTED_RESULTS['ymean'].append(sum(headY) * pixelSize / len(headY))
        _EXPECTED_RESULTS['binaryClass25degMaxTailAngle'].append(1 if max(map(lambda x: math.degrees(abs(x)), angles)) > 25 else 0)
        _EXPECTED_RESULTS['tailAngleIntegralSigned'].append(sum(map(math.degrees, angles)))
        _EXPECTED_RESULTS['BoutFrameNumberStart'].append(startFrame)
        _EXPECTED_RESULTS['tailAngleSymmetry'].append(-sorted((min(angles), max(angles)), key=abs)[0] / sorted((min(angles), max(angles)), key=abs)[1])
        _EXPECTED_RESULTS['secondBendAmpDividedByFirst'].append(degreeBendAmplitudes[1] / degreeBendAmplitudes[0])
        _EXPECTED_RESULTS['tailAngleIntegral'].append(sum(map(lambda x: abs(math.degrees(x)), angles)))
        _EXPECTED_RESULTS['percentTimeSpentSwimming'].append(100 * sum(boutDurations) / (lastFrame - firstFrame))
        _FIRST_BOUT_REMOVED_RESULTS['percentTimeSpentSwimming'].append(100 * sum(boutDurations[1:]) / (lastFrame - firstFrame) if not videoIdx and not wellIdx else _EXPECTED_RESULTS['percentTimeSpentSwimming'][-1])
        _EXPECTED_RESULTS['Bout Counts'].append(numberOfBouts)
        _FIRST_BOUT_REMOVED_RESULTS['Bout Counts'].append(numberOfBouts - 1 if not videoIdx and not wellIdx else _EXPECTED_RESULTS['Bout Counts'][-1])
        _EXPECTED_RESULTS['Bout Rate (bouts / s)'].append(numberOfBouts * fps / (lastFrame - firstFrame))
        _FIRST_BOUT_REMOVED_RESULTS['Bout Rate (bouts / s)'].append((numberOfBouts - 1) * fps / (lastFrame - firstFrame) if not videoIdx and not wellIdx else _EXPECTED_RESULTS['Bout Rate (bouts / s)'][-1])
      wellPoissMouv.append([wellBouts])
    results['wellPoissMouv'] = wellPoissMouv
    resultsList.append(results)
  return resultsList


@pytest.fixture(scope="module", autouse=True)
def _createResultsFolder():
  with open(os.path.join(paths.getConfigurationFolder(), '4wellsZebrafishLarvaeEscapeResponses.json')) as configFile:
    config = json.load(configFile)

  generatedResults = _generateResults()
  with h5py.File(os.path.join(paths.getDefaultZZoutputFolder(), _VIDEO_NAMES[0]), 'w') as results:
    superStruct = generatedResults[0]
    for idx, wellPositions in enumerate(superStruct['wellPositions']):
      results.require_group(f"wellPositions/well{idx}").attrs.update(wellPositions)
    config['nbWells'] = _WELLS_PER_VIDEO[0]
    results.require_group("configurationFileUsed").attrs.update(config)
    results.attrs['version'] = 0
    results.attrs['firstFrame'] = superStruct["firstFrame"]
    results.attrs['lastFrame'] = superStruct['lastFrame']
    results.attrs['videoFPS'] = _FPS[0]
    results.attrs['videoPixelSize'] = _PIXEL_SIZES[0]
    results.create_dataset('exampleFrame', data=np.zeros((1, 1, 1)))
    if 'pathToOriginalVideo' in superStruct:
      results.attrs['pathToOriginalVideo'] = superStruct['pathToOriginalVideo']
    for wellIdx, well in enumerate(superStruct['wellPoissMouv']):
      for animalIdx, animal in enumerate(well):
        perFrameData = {}
        listOfBouts = results.require_group(f"dataForWell{wellIdx}/dataForAnimal{animalIdx}/listOfBouts")
        listOfBouts.attrs['numberOfBouts'] = len(animal)
        for boutIdx, bout in enumerate(animal):
          boutGroup = listOfBouts.require_group(f'bout{boutIdx}')
          boutGroup.attrs['BoutStart'] = bout['BoutStart']
          boutGroup.attrs['BoutEnd'] = bout['BoutEnd']
          boutStart = bout['BoutStart'] - superStruct['firstFrame']
          boutEnd = bout['BoutEnd'] - superStruct['firstFrame'] + 1
          for key, value in bout.items():
            if key == 'AnimalNumber':
              continue
            if key in ('HeadX', 'HeadY'):
              if 'HeadPos' not in perFrameData:
                headPosData = np.empty(superStruct['lastFrame'] - superStruct['firstFrame'] + 1, dtype=[('X', float), ('Y', float)])
                headPosData[:] = np.nan
                perFrameData['HeadPos'] = headPosData
              perFrameData['HeadPos'][key[-1]][boutStart:boutEnd] = value
            elif key in ('Heading', 'TailAngle_Raw'):
              if key == 'TailAngle_Raw':
                key = 'TailAngle'
              if key not in perFrameData:
                data = np.empty(superStruct['lastFrame'] - superStruct['firstFrame'] + 1, dtype=float)
                data[:] = np.nan
                perFrameData[key] = data
              perFrameData[key][boutStart:boutEnd] = value
            elif key in ('TailX_VideoReferential', 'TailY_VideoReferential'):
              key = f'TailPos{key[4]}'
              value = np.array(value).T
              if key not in perFrameData:
                headPosData = np.empty(superStruct['lastFrame'] - superStruct['firstFrame'] + 1, dtype=[(f'Pos{idx + 1}', float) for idx in range(value.shape[0] - 1)])
                headPosData[:] = np.nan
                perFrameData[key] = headPosData
              for idx, val in enumerate(value[1:]):
                perFrameData[key][f'Pos{idx + 1}'][boutStart:boutEnd] = val
            elif isinstance(value, list):
              boutGroup.create_dataset(key, data=np.array(value))
            else:
              boutGroup.attrs[key] = value
        for key, data in perFrameData.items():
          dataset = results.create_dataset(f"dataForWell{wellIdx}/dataForAnimal{animalIdx}/dataPerFrame/{key}", data=data)
          if len(data.dtype):
            dataset.attrs['columns'] = data.dtype.names
    from zebrazoom.dataAPI._createSuperStructFromH5 import createSuperStructFromH5
    assert createSuperStructFromH5(results)['wellPoissMouv'] == superStruct['wellPoissMouv']

  for nbWells, name, results in zip(_WELLS_PER_VIDEO[1:], _VIDEO_NAMES[1:], generatedResults[1:]):
    folder = os.path.join(paths.getDefaultZZoutputFolder(), name)
    os.mkdir(folder)
    with open(os.path.join(folder, 'intermediaryWellPosition.txt'), 'wb') as wellPositionsFile:
      pickle.dump(results['wellPositions'], wellPositionsFile)
    config['nbWells'] = nbWells
    with open(os.path.join(folder, 'configUsed.json'), 'w') as configFile:
      json.dump(config, configFile)
    with open(os.path.join(folder, 'results_%s.txt' % name), 'w') as resultsFile:
      json.dump(results, resultsFile)


def _enterCellText(qtbot, table, row, column, text):
  x = table.columnViewportPosition(column)
  y = table.rowViewportPosition(row)
  qtbot.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, y))
  qtbot.waitUntil(lambda: table.selectionModel().currentIndex() == table.model().index(row, column), timeout=20000)
  qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, y))
  qtbot.keyClicks(table.viewport().focusWidget(), text)
  qtbot.keyClick(table.viewport().focusWidget(), Qt.Key.Key_Return)
  qtbot.waitUntil(lambda: table.model().data(table.selectionModel().currentIndex()) == text, timeout=20000)


def _enterRowValues(qtbot, table, row, values):
  assert len(values) == 5
  for col, value in zip(range(2, 7), values):
    _enterCellText(qtbot, table, row, col, value)


def _goToCreateExcelPage(qapp, qtbot):
  startPage = qapp.window.centralWidget().layout().currentWidget()
  assert isinstance(startPage, StartPage)
  circle = list(startPage._flowchart.iterCircleRects())[-1]
  qtbot.mouseMove(startPage, pos=QPoint(0, 0))
  qtbot.mouseMove(startPage, pos=QPoint(circle.x() + circle.width() // 2, circle.y() + circle.height()))
  qtbot.waitUntil(lambda: startPage._shownDetail is startPage._detailsWidgets[-1], timeout=20000)
  qtbot.mouseClick(startPage._shownDetail._analyzeOutputBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), CreateExperimentOrganizationExcel), timeout=20000)
  assert qapp.window.centralWidget().layout().currentWidget()._tree.selectedIndexes() == []
  return qapp.window.centralWidget().layout().currentWidget()


def _selectExperiment(createExcelPage, qapp, qtbot, name):
  experimentIndex = createExcelPage._tree.model().index(os.path.join(createExcelPage._tree.model().rootPath(), name))
  qtbot.mouseClick(createExcelPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=createExcelPage._tree.visualRect(experimentIndex).center())
  qapp.processEvents()
  qtbot.waitUntil(lambda: createExcelPage._tree.selectedIndexes() == [experimentIndex], timeout=20000)


count = [1]
def _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices=None, conditions=None, genotypes=None):
  videos = [name for idx, name in enumerate(_VIDEO_NAMES) if idx in indices] if indices is not None else _VIDEO_NAMES
  fpsList = [fps for idx, fps in enumerate(_FPS) if idx in indices] if indices is not None else _FPS
  pixelSizes = [pixelSize for idx, pixelSize in enumerate(_PIXEL_SIZES) if idx in indices] if indices is not None else _PIXEL_SIZES
  if conditions is None:
    conditions = _CONDITIONS
  if genotypes is None:
    genotypes = _GENOTYPES
  qapp.processEvents()
  qtbot.mouseClick(createExcelPage._newExperimentBtn, Qt.MouseButton.LeftButton)
  qapp.processEvents()
  qtbot.waitUntil(lambda: createExcelPage._tree.selectedIndexes() == [createExcelPage._tree.model().index(os.path.join(createExcelPage._tree.model().rootPath(), 'Experiment %d.xlsx' % count[0]))], timeout=20000)
  count[0] += 1
  qtbot.waitUntil(lambda: createExcelPage._table.model().rowCount() == 0, timeout=20000)
  monkeypatch.setattr(createExcelPage, '_getMultipleFolders', lambda *args: [os.path.join(qapp.ZZoutputLocation, video) for video in videos])
  qtbot.mouseClick(createExcelPage._addVideosBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: createExcelPage._table.model().rowCount() == len(videos), timeout=20000)
  for idx, (fps, pixelSize, condition, genotype) in enumerate(zip(fpsList, pixelSizes, conditions, genotypes)):
    include = '[%s]' % ', '.join('1' for _ in range(_WELLS_PER_VIDEO[sorted(indices)[idx] if indices is not None else idx]))
    _enterRowValues(qtbot, createExcelPage._table, idx, (str(fps), str(pixelSize), condition, genotype, include))


def _resetPopulationComparisonPageState(page, qapp):  # this is required because the page is persisted as long as the app is running
  for checkable in (page._keepDiscardedBoutsCheckbox, page._saveInMatlabFormatCheckbox, page._saveRawDataCheckbox,
                    page._forcePandasRecreation, page._advancedOptionsExpander._toggleButton):
    checkable.setChecked(False)
  page._frameStepForDistanceCalculation.setText('')
  page._minNbBendForBoutDetect.setText('')
  page._noOutlierRemovalButton.setChecked(True)
  page._tailTrackingParametersCheckbox.setChecked(True)
  qapp.processEvents()


def _test_kinematic_parameters_small_check_results():
  videoIndices = set([idx for idx in range(len(_VIDEO_NAMES)) if 2 < _WELLS_PER_VIDEO[idx] < 6][:2])
  conditionsList = [(('condition1', 'condition1', 'condition2', 'condition2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[0]]],
                    (('condition1', 'condition2', 'condition1', 'condition2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[1]]]]
  genotypesList = [(('genotype1', 'genotype1', 'genotype2', 'genotype2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[0]]],
                   (('genotype1', 'genotype2', 'genotype1', 'genotype2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[1]]]]
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 1')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]
  trialIds = {_VIDEO_NAMES[idx]: row for row, idx in enumerate(sorted(videoIndices))}
  expectedResultsDict = {k: [x for video, x in zip(_EXPECTED_RESULTS['Trial_ID'], v) if video in trialIds]
                         for k, v in _EXPECTED_RESULTS.items()}
  expectedResultsDict['Condition'] = [conditionsList[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsDict['Trial_ID'], expectedResultsDict['Well_ID'])]
  expectedResultsDict['Genotype'] = [genotypesList[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsDict['Trial_ID'], expectedResultsDict['Well_ID'])]
  expectedResultsAll = pd.DataFrame(expectedResultsDict).astype(generatedExcelAll.dtypes.to_dict())
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]
  expectedResultsMedian = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False).median(numeric_only=True)
  expectedResultsMedian['Condition'] = [conditionsList[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [genotypesList[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):
    chartCount = 7 if folder == 'allBoutsMixed' else 8
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)} | {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


def test_kinematic_parameters_small(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  videoIndices = set([idx for idx in range(len(_VIDEO_NAMES)) if 2 < _WELLS_PER_VIDEO[idx] < 6][:2])
  assert len(videoIndices) == 2
  conditionsList = [(('condition1', 'condition1', 'condition2', 'condition2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[0]]],
                    (('condition1', 'condition2', 'condition1', 'condition2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[1]]]]
  genotypesList = [(('genotype1', 'genotype1', 'genotype2', 'genotype2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[0]]],
                   (('genotype1', 'genotype2', 'genotype1', 'genotype2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[1]]]]
  conditions = map(lambda x: '[%s]' % ','.join(x), conditionsList)
  genotypes = map(lambda x: '[%s]' % ','.join(x), genotypesList)
  _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices=videoIndices, conditions=conditions, genotypes=genotypes)
  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_kinematic_parameters_small_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _enterChar(qapp, qtbot, widget, text):
  if not isinstance(widget, QComboBox):
    for _ in range(10):
      qtbot.keyClick(widget, Qt.Key.Key_Delete)
  qtbot.keyClick(widget, text)
  if not isinstance(widget, QComboBox):
    qtbot.keyClick(widget, Qt.Key.Key_Return)
  qapp.processEvents()


@pytest.mark.skipif(sys.platform == 'darwin', reason='fails on Mac GitHub runner')
def test_visualization_filters(qapp, qtbot, monkeypatch, tmp_path):
  # Generate results files
  allBoutsFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Test Experiment', 'allBoutsMixed')
  os.makedirs(allBoutsFolder)
  medianFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Test Experiment', 'medianPerWellFirst')
  os.makedirs(medianFolder)
  columns = ['Bout Speed (mm/s)', 'Number of Oscillations', 'maxTailAngleAmplitude']
  ignoredKeys = [key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS | set(columns)]
  medianData = pd.DataFrame(index=pd.MultiIndex.from_product([[0, 1]] * len(columns), names=columns)).reset_index()
  rowCount = 2 ** len(columns)
  for key in ignoredKeys:
    if key == 'Bout Duration (s)' or key == 'Genotype':
      continue
    medianData.insert(len(medianData.columns), key, 1)
  medianData.insert(0, 'Bout Duration (s)', 1)
  medianData.insert(0, 'Genotype', ['trial%d' % idx for idx in range(rowCount)])
  medianData.to_excel(os.path.join(medianFolder, 'globalParametersInsideCategories.xlsx'), index=False)
  pd.DataFrame().to_excel(os.path.join(allBoutsFolder, 'globalParametersInsideCategories.xlsx'), index=False)

  # Go to previous results page and select test results
  qtbot.mouseClick(_goToCreateExcelPage(qapp, qtbot)._previousParameterResultsBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not isinstance(qapp.window.centralWidget().layout().currentWidget(), CreateExperimentOrganizationExcel), timeout=20000)
  resultsPage = qapp.window.centralWidget().layout().currentWidget()
  assert resultsPage._tree.selectedIndexes() == []
  resultsIndex = resultsPage._tree.model().mapFromSource(resultsPage._tree.model().sourceModel().index(os.path.join(resultsPage._tree.model().sourceModel().rootPath(), 'Test Experiment'))).siblingAtColumn(0)
  qtbot.mouseClick(resultsPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=resultsPage._tree.visualRect(resultsIndex).center())
  qapp.processEvents()  # this needs to be called at various places to make sure the charts are redrawn
  qtbot.waitUntil(lambda: [index.row() for index in resultsPage._tree.selectedIndexes()] == [resultsIndex.row()], timeout=20000)

  # Go to All parameters tab
  tabBar = resultsPage._mainWidget.layout().itemAt(1).widget().tabBar()
  qtbot.mouseClick(tabBar, Qt.MouseButton.LeftButton, pos=tabBar.tabRect(4).center())
  qtbot.waitUntil(lambda: tabBar.currentIndex() == 4, timeout=20000)

  # Prepare test function
  expectedGenotypes = None

  originalMethod = resultsPage._plotFigure
  def _plotFigure(param, figure, data, plotOutliersAndMean, plotPoints):
    assert expectedGenotypes is not None
    assert expectedGenotypes == set(data['Genotype'])
    originalMethod(param, figure, data, plotOutliersAndMean, plotPoints)
    qapp.processEvents()
    # Test export
    qtbot.mouseClick(resultsPage._exportDataBtn, Qt.MouseButton.LeftButton)
    exportedData = pd.read_excel(exportedFile)
    columnsValues = {genotype: dict(zip(columns, map(int, "{0:03b}".format(int(genotype[-1]))))) for genotype in expectedGenotypes}
    expectedData = {'%s %s 1' % (param, genotype): [columnsValues[genotype][param] if param in columns else 1] for param, checkbox in resultsPage._paramCheckboxes.items() if checkbox.isChecked() for genotype in expectedGenotypes}
    assert set(exportedData.columns) == set(expectedData)
    assert_frame_equal(exportedData, pd.DataFrame({col: expectedData[col] for col in exportedData.columns}))
  monkeypatch.setattr(resultsPage, '_plotFigure', _plotFigure)

  # Prepare for testing export
  exportedFile = tmp_path / "asd.xlsx"
  monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (exportedFile, None))

  # Add and modify some filters
  assert not resultsPage._filters
  qtbot.mouseClick(resultsPage._addFilterBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: len(resultsPage._filters) == 1, timeout=20000)
  qapp.processEvents()
  filter0 = resultsPage._filters[0]
  _enterChar(qapp, qtbot, filter0._minimumSpinbox, '1')
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount)}
  _enterChar(qapp, qtbot, filter0._maximumSpinbox, '1')
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount // 2, rowCount)}
  _enterChar(qapp, qtbot, filter0._nameComboBox, columns[0][0])
  assert filter0.name() == columns[0]
  expectedGenotypes = {'trial%d' % idx for idx in range(1, rowCount, 2)}
  _enterChar(qapp, qtbot, filter0._nameComboBox, columns[-1][0])
  assert filter0.name() == columns[-1]

  qtbot.mouseClick(resultsPage._addFilterBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: len(resultsPage._filters) == 2, timeout=20000)
  qapp.processEvents()
  filter1 = resultsPage._filters[1]
  _enterChar(qapp, qtbot, filter1._maximumSpinbox, '1')
  _enterChar(qapp, qtbot, filter1._minimumSpinbox, '1')
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount // 2 + 1, rowCount, 2)}
  _enterChar(qapp, qtbot, filter1._nameComboBox, columns[0][0])
  assert filter1.name() == columns[0]

  # Remove filters
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount // 2, rowCount)}
  qtbot.mouseClick(filter0._removeBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: len(resultsPage._filters) == 1, timeout=20000)
  qapp.processEvents()

  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount)}
  qtbot.mouseClick(filter1._removeBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not resultsPage._filters, timeout=20000)
  qapp.processEvents()


def _test_basic_check_results(expectedResults=_EXPECTED_RESULTS):
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _DEFAULT_KEYS if key not in _MEDIAN_ONLY_KEYS]
  expectedResultsAll = pd.DataFrame(expectedResults).astype(generatedExcelAll.dtypes.to_dict())
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _DEFAULT_KEYS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _DEFAULT_KEYS if key not in _ALL_ONLY_KEYS]
  expectedResultsMedian = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False).median(numeric_only=True)
  trialIds = {trialId: idx for idx, trialId in enumerate(_VIDEO_NAMES)}
  expectedResultsMedian['Condition'] = [_CONDITIONS_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [_GENOTYPES_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _DEFAULT_KEYS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))
  dataFolder = os.path.join(paths.getDataAnalysisFolder(), 'data')
  pickleFile = os.path.join(dataFolder, 'Experiment 2.pkl')
  assert os.path.exists(pickleFile)
  with open(pickleFile, 'rb') as f:
    dataframe = pickle.load(f).astype(generatedExcelAll.dtypes.to_dict())
  for col in (key for key in _DEFAULT_KEYS if key not in _MEDIAN_ONLY_KEYS):
    assert_series_equal(expectedResultsAll[col], dataframe[col])
  assert not os.path.exists(os.path.join(dataFolder, 'Experiment 2.mat'))

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):
    chartCount = 3
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)} | {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_basic(qapp, qtbot, monkeypatch):
  import zebrazoom.dataAPI
  zebrazoom.dataAPI.getKinematicParametersPerBout('test1', 0, 0, 0)  # force parameter calculation

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch)
  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked(), timeout=20000)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_basic_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


@pytest.mark.long
def test_force_recalculation(qapp, qtbot, monkeypatch):
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json'))
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'test4.pkl'))
  mtime = os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices={0, 3}, conditions=[_CONDITIONS[0], _CONDITIONS[3]], genotypes=[_GENOTYPES[0], _GENOTYPES[3]])
  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked(), timeout=20000)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  # ensure parameters were not recalculated
  assert mtime == os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 3.xlsx')

  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._forcePandasRecreation, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._forcePandasRecreation.isChecked, timeout=20000)

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  # ensure parameters were recalculated
  assert mtime != os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


@pytest.mark.long
def test_force_recalculation_from_dialog(qapp, qtbot, monkeypatch):
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json'))
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'test4.pkl'))
  mtime = os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices={3}, conditions=[_CONDITIONS[3]], genotypes=[_GENOTYPES[3]])
  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked(), timeout=20000)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  # ensure parameters were not recalculated
  assert mtime == os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: True)

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 3.xlsx')

  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  # ensure parameters were recalculated
  assert mtime != os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _test_kinematic_parameters_large_check_results():
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  dataFolder = os.path.join(paths.getDataAnalysisFolder(), 'data')
  #assert os.path.exists(os.path.join(dataFolder, 'Experiment 2.mat'))  # ensure matlab file was created
  #os.remove(os.path.join(dataFolder, 'Experiment 2.mat'))  # delete the file so it doesn't mess with later tests
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]
  expectedResultsAll = pd.DataFrame(_EXPECTED_RESULTS).astype(generatedExcelAll.dtypes.to_dict())
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]
  expectedResultsMedian = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False).median(numeric_only=True)
  trialIds = {trialId: idx for idx, trialId in enumerate(_VIDEO_NAMES)}
  expectedResultsMedian['Condition'] = [_CONDITIONS_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [_GENOTYPES_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))
  pickleFile = os.path.join(dataFolder, 'Experiment 2.pkl')
  assert os.path.exists(pickleFile)
  with open(pickleFile, 'rb') as f:
    dataframe = pickle.load(f).astype(generatedExcelAll.dtypes.to_dict())
  for col in (key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS):
    assert_series_equal(expectedResultsAll[col], dataframe[col])

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):
    chartCount = 7 if folder == 'allBoutsMixed' else 8
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)} | {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_kinematic_parameters_large(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
  #qtbot.mouseClick(populationComparisonPage._saveInMatlabFormatCheckbox, Qt.MouseButton.LeftButton)
  #qtbot.waitUntil(populationComparisonPage._saveInMatlabFormatCheckbox.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_kinematic_parameters_large_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _test_frames_for_distance_calculation_check_results():
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _DEFAULT_KEYS if key not in _MEDIAN_ONLY_KEYS]
  trialIds = {name: idx for idx, name in enumerate(_VIDEO_NAMES)}
  expectedResultsDict = {k: v[:] for k, v in _EXPECTED_RESULTS.items()}
  expectedResultsDict['Bout Speed (mm/s)'] = [(speed / distance) * (distance + (distance / (end - start)) * 2)for speed, distance, start, end in
                                  zip(expectedResultsDict['Bout Speed (mm/s)'], expectedResultsDict['Bout Distance (mm)'], _EXPECTED_RESULTS['BoutStart'], _EXPECTED_RESULTS['BoutEnd'])]
  expectedResultsDict['Bout Distance (mm)'] = [distance + (distance / (end - start)) * 2 for distance, start, end in
                                          zip(expectedResultsDict['Bout Distance (mm)'], _EXPECTED_RESULTS['BoutStart'], _EXPECTED_RESULTS['BoutEnd'])]
  expectedResultsAll = pd.DataFrame(expectedResultsDict).astype(generatedExcelAll.dtypes.to_dict())
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _DEFAULT_KEYS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _DEFAULT_KEYS if key not in _ALL_ONLY_KEYS]
  expectedResultsMedian = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False).median(numeric_only=True)
  trialIds = {trialId: idx for idx, trialId in enumerate(_VIDEO_NAMES)}
  expectedResultsMedian['Condition'] = [_CONDITIONS_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [_GENOTYPES_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _DEFAULT_KEYS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))
  dataFolder = os.path.join(paths.getDataAnalysisFolder(), 'data')
  pickleFile = os.path.join(dataFolder, 'Experiment 2.pkl')
  assert os.path.exists(pickleFile)
  with open(pickleFile, 'rb') as f:
    dataframe = pickle.load(f).astype(generatedExcelAll.dtypes.to_dict())
  for col in (key for key in _DEFAULT_KEYS if key not in _MEDIAN_ONLY_KEYS):
    assert_series_equal(expectedResultsAll[col], dataframe[col])

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):
    chartCount = 3
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)} | {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_frames_for_distance_calculation(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked(), timeout=20000)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._frameStepForDistanceCalculation, Qt.MouseButton.LeftButton)
  qtbot.keyClicks(populationComparisonPage._frameStepForDistanceCalculation, '1')
  qtbot.waitUntil(lambda: populationComparisonPage._frameStepForDistanceCalculation.text() == '1', timeout=20000)

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_frames_for_distance_calculation_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _test_minimum_number_of_bends_check_results():
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]
  colsToKeep = {'Trial_ID', 'Well_ID', 'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration'}
  expectedResultsDict = {k: [x if numOfOsc * 2 >= 12 or k in colsToKeep else np.nan for x, numOfOsc in zip(v, _EXPECTED_RESULTS['Number of Oscillations'])]
                         for k, v in _EXPECTED_RESULTS.items()}
  assert expectedResultsDict['Bout Duration (s)'].count(np.nan) > 0  # make sure some bouts were discarded
  expectedResultsAll = pd.DataFrame(expectedResultsDict).astype(generatedExcelAll.dtypes.to_dict())
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]
  groupedResults = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False)
  expectedResultsMedian = groupedResults.median(numeric_only=True)
  trialIds = {trialId: idx for idx, trialId in enumerate(_VIDEO_NAMES)}
  expectedResultsMedian['Condition'] = [_CONDITIONS_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [_GENOTYPES_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  expectedResultsMedian['Bout Counts'] = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'])['Number of Oscillations'].apply(lambda x: (x * 2 >= 12).sum()).reset_index(name='count')['count']
  expectedResultsMedian['Bout Rate (bouts / s)'] = expectedResultsMedian['Bout Counts'] / expectedResultsMedian['videoDuration']
  expectedResultsMedian['percentTimeSpentSwimming'] = groupedResults['Bout Duration (s)'].sum()['Bout Duration (s)'].div(expectedResultsMedian['videoDuration']).mul(100)
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):  # no charts with outliers
    chartCount = 7 if folder == 'allBoutsMixed' else 8
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_minimum_number_of_bends(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._bendsOutlierRemovalButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._bendsOutlierRemovalButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._minNbBendForBoutDetect, Qt.MouseButton.LeftButton)
  qtbot.keyClicks(populationComparisonPage._minNbBendForBoutDetect, '12')
  qtbot.waitUntil(lambda: populationComparisonPage._minNbBendForBoutDetect.text() == '12', timeout=20000)

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_minimum_number_of_bends_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _test_keep_data_for_discarded_bouts_check_results():
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]
  colsToKeep = {'Trial_ID', 'Well_ID', 'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration', 'Bout Distance (mm)', 'Bout Duration (s)', 'Bout Speed (mm/s)', 'Absolute Yaw (deg) (from heading vals)', 'Signed Yaw (deg) (from heading vals)', 'headingRangeWidth', 'IBI (s)', 'Angular Velocity (deg/s)'}
  expectedResultsDict = {k: [x if numOfOsc * 2 >= 12 or k in colsToKeep else np.nan for x, numOfOsc in zip(v, _EXPECTED_RESULTS['Number of Oscillations'])]
                         for k, v in _EXPECTED_RESULTS.items()}
  assert expectedResultsDict['xmean'].count(np.nan) > 0  # make sure some bouts were discarded
  expectedResultsAll = pd.DataFrame(expectedResultsDict).astype(generatedExcelAll.dtypes.to_dict())
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]
  groupedResults = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False)
  expectedResultsMedian = groupedResults.median(numeric_only=True)
  trialIds = {trialId: idx for idx, trialId in enumerate(_VIDEO_NAMES)}
  expectedResultsMedian['Condition'] = [_CONDITIONS_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [_GENOTYPES_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  expectedResultsMedian['percentTimeSpentSwimming'] = groupedResults['Bout Duration (s)'].sum()['Bout Duration (s)'].div(expectedResultsMedian['videoDuration']).mul(100)
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):  # no charts with outliers
    chartCount = 7 if folder == 'allBoutsMixed' else 8
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_keep_data_for_discarded_bouts(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._bendsOutlierRemovalButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._bendsOutlierRemovalButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._keepDiscardedBoutsCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._keepDiscardedBoutsCheckbox.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._minNbBendForBoutDetect, Qt.MouseButton.LeftButton)
  qtbot.keyClicks(populationComparisonPage._minNbBendForBoutDetect, '12')

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_keep_data_for_discarded_bouts_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _test_gaussian_outlier_removal():
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  dataFolder = os.path.join(paths.getDataAnalysisFolder(), 'data')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]
  expectedResultsAll = pd.DataFrame(_EXPECTED_RESULTS).astype(generatedExcelAll.dtypes.to_dict())
  colsToKeep = {'Trial_ID', 'Well_ID', 'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration'}
  columnsToCheckForOutliers = ('Bout Duration (s)', 'Bout Distance (mm)', 'Number of Oscillations', 'Max absolute TBA (deg.)', 'Absolute Yaw (deg)')
  expectedResultsAll.loc[(np.abs(scipy.stats.zscore(expectedResultsAll[columnsToCheck].astype(float), nan_policy='omit')) > 3).any(axis=1), ~expectedResultsAll.columns.isin(colsToKeep)] = np.nan
  assert_frame_equal(generatedExcelAll, expectedResultsAll[[key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]])
  generatedExcelMedian = pd.read_excel(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))
  assert list(generatedExcelMedian.columns) == [key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]
  expectedResultsMedian = expectedResultsAll.groupby(['Trial_ID', 'Well_ID'], as_index=False).median(numeric_only=True)
  trialIds = {trialId: idx for idx, trialId in enumerate(_VIDEO_NAMES)}
  expectedResultsMedian['Condition'] = [_CONDITIONS_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  expectedResultsMedian['Genotype'] = [_GENOTYPES_LIST[trialIds[trialId]][wellIdx] for trialId, wellIdx in zip(expectedResultsMedian['Trial_ID'], expectedResultsMedian['Well_ID'])]
  seen = set()
  expectedResultsMedian['Trial_ID'] = [x if x not in seen and not seen.add(x) else np.nan for x in expectedResultsMedian['Trial_ID']]
  assert_frame_equal(generatedExcelMedian, expectedResultsMedian[[key for key in _EXPECTED_RESULTS if key not in _ALL_ONLY_KEYS]].astype(generatedExcelMedian.dtypes.to_dict()))
  pickleFile = os.path.join(dataFolder, 'Experiment 2.pkl')
  assert os.path.exists(pickleFile)
  with open(pickleFile, 'rb') as f:
    dataframe = pickle.load(f).astype(generatedExcelAll.dtypes.to_dict())
  for col in (key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS):
    assert_series_equal(expectedResultsAll[col], dataframe[col])

  for folder in ('allBoutsMixed', 'medianPerWellFirst'):
    chartCount = 7 if folder == 'allBoutsMixed' else 8
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_gaussian_outlier_removal(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._gaussianOutlierRemovalButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._gaussianOutlierRemovalButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_kinematic_parameters_small_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


def _goToVisualizationPage(qapp, qtbot):
  startPage = qapp.window.centralWidget().layout().currentWidget()
  assert isinstance(startPage, StartPage)
  circle = list(startPage._flowchart.iterCircleRects())[-2]
  qtbot.mouseMove(startPage, pos=QPoint(circle.x() + circle.width() // 2, circle.y() + circle.height()))
  qtbot.waitUntil(lambda: startPage._shownDetail is startPage._detailsWidgets[-2], timeout=20000)
  qtbot.mouseClick(startPage._shownDetail._visualizeOutputBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ViewParameters), timeout=20000)
  viewParametersPage = qapp.window.centralWidget().layout().currentWidget()
  qapp.processEvents()
  assert viewParametersPage._tree.selectedIndexes() == []
  return viewParametersPage


@pytest.mark.long
def test_flagged_bouts(qapp, qtbot, monkeypatch):
  viewParametersPage = _goToVisualizationPage(qapp, qtbot)

  # Select the first test result folder
  resultsItem = next(results for results in viewParametersPage._tree.model().sourceModel().rootItem.iter_paths() if results.filename.endswith('test1.h5'))
  resultsIndex = viewParametersPage._tree.model().mapFromSource(viewParametersPage._tree.model().sourceModel().createIndex(resultsItem.childNumber(), 0, resultsItem))
  qtbot.mouseClick(viewParametersPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=viewParametersPage._tree.visualRect(resultsIndex).center())
  qapp.processEvents()
  qtbot.waitUntil(lambda: resultsIndex in viewParametersPage._tree.selectedIndexes(), timeout=20000)

  # Flag the first bout and save the changes
  assert viewParametersPage.flag_movement_btn.text() == 'Flag Movement'
  qtbot.mouseClick(viewParametersPage.flag_movement_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(viewParametersPage.superstruct_btn.isVisible, timeout=20000)
  qtbot.mouseClick(viewParametersPage.superstruct_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not viewParametersPage.superstruct_btn.isVisible(), timeout=20000)

  # Go back to the start page
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked(), timeout=20000)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._forcePandasRecreation, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._forcePandasRecreation.isChecked, timeout=20000)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  expectedResults = _EXPECTED_RESULTS.copy()
  expectedResults.update(_FIRST_BOUT_REMOVED_RESULTS)
  _test_basic_check_results(expectedResults={param: values[1:] for param, values in expectedResults.items()})

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  viewParametersPage = _goToVisualizationPage(qapp, qtbot)

  # Select the first test result folder
  resultsItem = next(results for results in viewParametersPage._tree.model().sourceModel().rootItem.iter_paths() if results.filename.endswith('test1.h5'))
  resultsIndex = viewParametersPage._tree.model().mapFromSource(viewParametersPage._tree.model().sourceModel().createIndex(resultsItem.childNumber(), 0, resultsItem))
  qtbot.mouseClick(viewParametersPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=viewParametersPage._tree.visualRect(resultsIndex).center())
  qapp.processEvents()
  qtbot.waitUntil(lambda: resultsIndex in viewParametersPage._tree.selectedIndexes(), timeout=20000)

  # Unflag the first bout so it doesn't mess with later tests and save the changes
  assert viewParametersPage.flag_movement_btn.text() == 'UnFlag Movement'
  qtbot.mouseClick(viewParametersPage.flag_movement_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(viewParametersPage.superstruct_btn.isVisible, timeout=20000)
  qtbot.mouseClick(viewParametersPage.superstruct_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not viewParametersPage.superstruct_btn.isVisible(), timeout=20000)

  # Go back to the start page
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)


@pytest.mark.long
def test_alternative_ZZoutput(qapp, qtbot, monkeypatch, tmp_path):
  global _VIDEO_NAMES
  # create alternative ZZoutput folder, copy some results there and rename them
  defaultZZoutputLocation = qapp.ZZoutputLocation
  newFolder = d = tmp_path / "newZZoutput"
  newFolder.mkdir()
  videoIndices = set([idx for idx in range(len(_VIDEO_NAMES)) if 2 < _WELLS_PER_VIDEO[idx] < 6][:2])
  assert len(videoIndices) == 2
  newNames = [f'asd{idx}{_VIDEO_NAMES[idx]}' for idx in videoIndices]
  try:
    oldVideoNames = _VIDEO_NAMES[:]
    for idx, name in zip(videoIndices, newNames):
      shutil.copytree(os.path.join(defaultZZoutputLocation, _VIDEO_NAMES[idx]), os.path.join(newFolder, name))
      os.rename(os.path.join(newFolder, name, f'results_{_VIDEO_NAMES[idx]}.txt'), os.path.join(newFolder, name, f'results_{name}.txt'))
      _VIDEO_NAMES[idx] = name
    # set the new folder as the selected output folder and create the experiment
    monkeypatch.setattr(qapp, '_ZZoutputLocation', str(newFolder))
    createExcelPage = _goToCreateExcelPage(qapp, qtbot)
    conditionsList = [(('condition1', 'condition1', 'condition2', 'condition2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[0]]],
                      (('condition1', 'condition2', 'condition1', 'condition2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[1]]]]
    genotypesList = [(('genotype1', 'genotype1', 'genotype2', 'genotype2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[0]]],
                     (('genotype1', 'genotype2', 'genotype1', 'genotype2') * 2)[:_WELLS_PER_VIDEO[sorted(videoIndices)[1]]]]
    conditions = map(lambda x: '[%s]' % ','.join(x), conditionsList)
    genotypes = map(lambda x: '[%s]' % ','.join(x), genotypesList)
    _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices=videoIndices, conditions=conditions, genotypes=genotypes)
  finally:
    _VIDEO_NAMES = oldVideoNames

  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

  _test_kinematic_parameters_small_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  # set the default ZZoutput folder again and ensure errors are detected, set it back to the new folder and ensure no errors
  monkeypatch.setattr(qapp, '_ZZoutputLocation', defaultZZoutputLocation)
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, f'Experiment {count[0] - 1}.xlsx')
  assert createExcelPage._table.model().getErrors(createExcelPage._getWellPositions, createExcelPage._findResultsFile)
  monkeypatch.setattr(qapp, '_ZZoutputLocation', str(newFolder))
  assert not createExcelPage._table.model().getErrors(createExcelPage._getWellPositions, createExcelPage._findResultsFile)


@pytest.mark.long
def test_command_line(monkeypatch): # here we simply run the same experiments that were run through the gui using the command line instead
  from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis  # __main__ simply calls this

  experiment1 = os.path.join(paths.getDataAnalysisFolder(), 'experimentOrganizationExcel', 'Experiment 1.xlsx')
  experiment2 = os.path.join(paths.getDataAnalysisFolder(), 'experimentOrganizationExcel', 'Experiment 2.xlsx')
  experiment3 = os.path.join(paths.getDataAnalysisFolder(), 'experimentOrganizationExcel', 'Experiment 3.xlsx')

  # pathToExcelFile frameStepForDistanceCalculation minimumNumberOfBendsPerBout keepSpeedDistDurWhenLowNbBends thresholdInDegreesBetweenSfsAndTurns tailAngleKinematicParameterCalculation
  # saveRawDataInAllBoutsSuperStructure saveAllBoutsSuperStructuresInMatlabFormat forcePandasDfRecreation
  test_kinematic_parameters_small_params = [experiment1, '4', '0', '0', '-1', '1', '0', '0']
  test_basic_params = [experiment2, '4', '0', '0', '-1', '0', '0', '0', '1']
  test_force_recalculation_params = [experiment3, '4', '0', '0', '-1', '0', '0', '0', '1']
  test_kinematic_parameters_large_params = [experiment2, '4', '0', '0', '-1', '1', '0', '0']
  test_frames_for_distance_calculation_params = [experiment2, '1', '0', '0', '-1', '0', '0', '0']
  test_minimum_number_of_bends_params = [experiment2, '4', '12', '0', '-1', '1', '0', '0']
  test_keep_data_for_discarded_bouts_params = [experiment2, '4', '12', '1', '-1', '1', '0', '0']

  # test_kinematic_parameters_small
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_kinematic_parameters_small_params])
  kinematicParametersAnalysis(sys)
  _test_kinematic_parameters_small_check_results()

  # test_basic
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_basic_params])
  kinematicParametersAnalysis(sys)
  _test_basic_check_results()

  # test_force_recalculation
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json'))
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'test4.pkl'))
  mtime = os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_force_recalculation_params])
  kinematicParametersAnalysis(sys)
  assert mtime != os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  # test_kinematic_parameters_large
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_kinematic_parameters_large_params])
  kinematicParametersAnalysis(sys)
  _test_kinematic_parameters_large_check_results()

  # test_frames_for_distance_calculation
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_frames_for_distance_calculation_params])
  kinematicParametersAnalysis(sys)
  _test_frames_for_distance_calculation_check_results()

  # test_minimum_number_of_bends
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_minimum_number_of_bends_params])
  kinematicParametersAnalysis(sys)
  _test_minimum_number_of_bends_check_results()

  # test_keep_data_for_discarded_bouts
  monkeypatch.setattr(sys, 'argv', [sys.executable, 'dataPostProcessing', 'kinematicParametersAnalysis', *test_keep_data_for_discarded_bouts_params])
  kinematicParametersAnalysis(sys)
  _test_keep_data_for_discarded_bouts_check_results()


@pytest.fixture(scope="module", autouse=True)
def _createNoBendsResults():
  exampleFolder = os.path.join(paths.getDefaultZZoutputFolder(), 'example2')
  with open(os.path.join(exampleFolder, 'results_example2.txt')) as resultsFile:
    results = json.load(resultsFile)
  results['wellPoissMouv'][0][0].insert(0, {"FishNumber": 0, "BoutStart": 26, "BoutEnd": 69, "TailAngle_Raw": [-0.006240849113759772, -0.0014291519141478304, -0.005189203263117115, -0.005189203263117115, -0.005189203263117115, -0.002578232277180348, 0.0003340556913826731, 0.000278734896041577, -0.0030861869249614315, -0.001940030839442386, -0.011102082711870409, -0.004149595932529948, -0.004149595932529948, 0.00018380095078907033, 0.0008022518949815094, 0.0022852844260699, 0.005963617663057086, -0.003414938404719514, 0.0019987491958017856, 0.002914933188241875, 0.001889667366595127, 0.001889667366595127, -0.004345094873527522, -0.004345094873527522, -0.0023462273534153866, 0.0034467684015906386, 0.003281505643017546, -0.004695579021644747, 0.005561019853021598, 0.004491926632255172, -0.002432612943433554, -0.002432612943433554, -0.0015100132447782855, -0.0025823796688735356, 0.003265403822290125, 0.0011679095636880632, -0.0016276982511422844, -0.0006632430475219664, -0.0003086248572943262, -0.0020096795487853925, 0.0067385614049664255, 0.008237971037745595, 0.006080464142091735, 0.010583379081843702], "HeadX": [177.46630621591402, 177.6340714157911, 177.4575496591406, 177.4575496591406, 177.4575496591406, 177.4254491299831, 177.90105205254878, 177.91158511136712, 177.54045180240834, 177.84642624902912, 177.64131211881772, 177.2435881889299, 177.2435881889299, 177.58693065363465, 177.59711998920804, 177.64221688983469, 177.8053109354689, 177.52286091776554, 177.55750183647748, 177.64223658051623, 177.72877776285765, 177.72877776285765, 177.27670030164265, 177.27670030164265, 177.36020641613428, 177.80185471715893, 177.4514787451177, 177.81585502828872, 177.85465169879654, 177.35780065056215, 177.59281536787165, 177.59281536787165, 177.33935473179162, 177.1227657119071, 177.84859229098075, 177.6318910775451, 177.46499231293237, 177.58690837474592, 177.12444333383954, 177.72425395134155, 177.6978154606288, 177.22810665758809, 177.54810504566225, 177.84304101435143], "HeadY": [168.38554193980323, 168.15142567503992, 168.3963420979409, 168.3963420979409, 168.3963420979409, 168.41102939981525, 168.0634104511565, 168.02069666180142, 168.32150992365987, 168.0813773672233, 168.22622475334077, 168.5499291450399, 168.5499291450399, 168.28052206525524, 168.25458321536257, 168.13195251414436, 168.00981775952914, 168.33394543346478, 168.18978979281744, 168.14936260840312, 168.16982911700057, 168.16982911700057, 168.53113149551592, 168.53113149551592, 168.47093243661465, 168.11224165401367, 168.39206207434208, 168.0830217687362, 168.10084696873238, 168.46703005198495, 168.28736256852355, 168.28736256852355, 168.48902940628878, 168.674725879993, 168.0627108113251, 168.15849570431087, 168.32275697377992, 168.23109711355193, 168.66615319501196, 168.16071921131734, 168.18297544537444, 168.57391101249019, 168.20318632529663, 168.0685479214287], "Heading": [4.027430486466754, 4.02860299095207, 4.027373055702956, 4.027373055702956, 4.027373055702956, 4.027228994294419, 4.029710706030029, 4.029858853889207, 4.027843596501839, 4.029484095302494, 4.028427344647354, 4.0262642387522405, 4.0262642387522405, 4.028104816848055, 4.0282072821861785, 4.0286814933330035, 4.029540024939261, 4.0277529398447065, 4.0282505057189555, 4.028635179755518, 4.0288636421650414, 4.0288636421650414, 4.026422543879201, 4.026422543879201, 4.026855981214056, 4.0292560767001255, 4.027364646580762, 4.029379682106819, 4.029459181028436, 4.026858547158751, 4.028105811950157, 4.028105811950157, 4.026739561828792, 4.02553634949133, 4.029540872437529, 4.028577027854041, 4.027593717334018, 4.028236513837674, 4.025564753127871, 4.028873114784674, 4.028727355241096, 4.026149619200806, 4.028184095390478, 4.029507169098423], "TailX_VideoReferential": [[177.46630621591402, 194.85576563768146, 212.2353792173277, 229.02146424904538, 245.05229452683415, 261.09132576611637, 277.70181225859176, 294.38402063166467, 310.87614549164255, 328.35942104031176], [177.6340714157911, 194.85015361838992, 211.71142771440438, 228.31441022198575, 244.75561765928552, 261.13156654445515, 277.53877339564593, 294.07375473100944, 310.833027068697, 327.91310692685994], [177.4575496591406, 194.84957418211485, 212.21264717776234, 229.0781337890914, 245.31088431304966, 261.50846180666935, 278.1067517636302, 294.7531442137881, 311.22377280663534, 328.1869734464444], [177.4575496591406, 194.84957418211485, 212.21264717776234, 229.0781337890914, 245.31088431304966, 261.50846180666935, 278.1067517636302, 294.7531442137881, 311.22377280663534, 328.1869734464444], [177.4575496591406, 194.84957418211485, 212.21264717776234, 229.0781337890914, 245.31088431304966, 261.50846180666935, 278.1067517636302, 294.7531442137881, 311.22377280663534, 328.1869734464444], [177.4254491299831, 195.0215971487053, 212.19106636003949, 229.03202749103644, 245.64265126874707, 262.12110842022236, 278.5655696725131, 295.0742057526703, 311.7451873877448, 328.6766853047875], [177.90105205254878, 194.435770828782, 211.34634723696027, 228.03711063507743, 244.42283113725009, 260.71642760199364, 277.11099215224436, 293.7696616705104, 310.619924591509, 326.7322024179806], [177.91158511136712, 194.63397979484176, 211.74530825418523, 228.31714601294388, 244.35498154922934, 260.6229311655309, 277.40851028251564, 294.4021263406161, 311.257975091994, 327.630252288811], [177.54045180240834, 194.87343365697438, 211.74827712903436, 228.29373583999129, 244.63856341124827, 260.9115134642085, 277.2413396202749, 293.7567955008508, 310.58663472733906, 327.8596109211429], [177.84642624902912, 194.51048840990023, 211.6558355042918, 228.45355116125037, 244.62776995917622, 260.9742245867947, 277.76705066447, 294.5727463527222, 311.21269863267355, 328.52665598064834], [177.64131211881772, 194.25531917346603, 211.42872634126977, 228.25237141688646, 244.1052787706774, 260.24480104528715, 276.9733661994868, 293.5619014159951, 310.5200186503617, 328.68588989961523], [177.2435881889299, 194.99047354826928, 211.8556329070868, 228.16031787560442, 244.22578006404447, 260.3704499929003, 276.7702096529111, 293.39411998810266, 310.2020387326787, 327.1815860487372], [177.2435881889299, 194.99047354826928, 211.8556329070868, 228.16031787560442, 244.22578006404447, 260.3704499929003, 276.7702096529111, 293.39411998810266, 310.2020387326787, 327.1815860487372], [177.58693065363465, 194.84014826191492, 211.70297235526138, 228.27573222287722, 244.6587571539656, 260.9523764377298, 277.25691936337296, 293.6727152200983, 310.30009329710896, 327.2393828836082], [177.59711998920804, 194.821825802083, 211.712118173538, 228.34573937073807, 244.80043166084843, 261.1539373110343, 277.48399858846085, 293.86835776029324, 310.38475709369663, 327.1109388558361], [177.64221688983469, 194.679300206031, 211.44604559590297, 228.00866909925767, 244.4333867559021, 260.7864146056435, 277.1339686882889, 293.54226504364556, 310.0775197115204, 326.80594873172066], [177.8053109354689, 194.59137130587519, 211.36938413114154, 228.1114104942454, 244.78951147816406, 261.3757481658751, 277.8421816403559, 294.16087298458393, 310.30388328153657, 326.24327361419125], [177.52286091776554, 194.8315756449362, 212.34655366973698, 229.22180857309942, 245.46620812743495, 261.5985676499499, 277.89700088561, 294.3413238524267, 310.9761269923017, 328.3215045389033], [177.55750183647748, 194.8027657980327, 211.73549593396982, 228.42993050152447, 244.9603077579323, 261.4008659604292, 277.82584336625075, 294.3094782326326, 310.9260088168106, 327.74967337602044], [177.64223658051623, 194.66246876278186, 211.45730235698127, 228.07424378339607, 244.56079946230793, 260.96447581399866, 277.33277925875007, 293.7132162168437, 310.15329310856134, 326.70051635418474], [177.72877776285765, 194.8362768523578, 211.75800428130904, 228.20965164711524, 244.36565136607004, 260.68710931619734, 277.34587927845956, 294.15949353526315, 310.9244076900442, 327.437077346239], [177.72877776285765, 194.8362768523578, 211.75800428130904, 228.20965164711524, 244.36565136607004, 260.68710931619734, 277.34587927845956, 294.15949353526315, 310.9244076900442, 327.437077346239], [177.27670030164265, 195.09095125089462, 212.14766028877756, 228.66758675128168, 244.87148997439698, 260.9801292941138, 277.2142640464222, 293.7946535673125, 310.94205719277454, 328.8772342587987], [177.27670030164265, 195.09095125089462, 212.14766028877756, 228.66758675128168, 244.87148997439698, 260.9801292941138, 277.2142640464222, 293.7946535673125, 310.94205719277454, 328.8772342587987], [177.36020641613428, 194.91407471103363, 211.99439598123686, 228.44818137432594, 244.47395357690536, 260.4873827657624, 276.7264132105795, 293.1760786364256, 309.8953186136105, 327.29677223990444], [177.80185471715893, 194.61087583866006, 211.4131074856868, 227.80916109870955, 243.86178296054126, 259.9451467659952, 276.24988358472484, 292.71052616341774, 309.2434781815517, 325.76514331860477], [177.4514787451177, 194.96134759816132, 211.93493032201678, 228.50829831826707, 244.81752298849545, 260.9986757342852, 277.1878279572194, 293.52105105888137, 310.1344164408541, 327.163995504721], [177.81585502828872, 194.47818007541767, 211.66383743450768, 228.3671066411138, 244.05786083583357, 260.1694824742833, 277.0202531284691, 293.4780589528612, 309.3037501031363, 327.65144444174297], [177.85465169879654, 194.59892636930448, 211.53636834579896, 228.32897033571345, 244.90920239036484, 261.360149850279, 277.7229035042667, 293.97443014466245, 310.1823596826873, 326.749598711121], [177.35780065056215, 195.03982653260277, 212.1271529951663, 228.76104356446712, 245.08276176671953, 261.2335711281381, 277.35473517493716, 293.5875174333312, 310.07318142953443, 326.9529906897614], [177.59281536787165, 194.68159678539791, 212.3469439391344, 228.92404274780847, 244.5505732938382, 260.46612889131205, 277.0849085597324, 293.79333897149496, 310.2408227823006, 327.25452832704], [177.59281536787165, 194.68159678539791, 212.3469439391344, 228.92404274780847, 244.5505732938382, 260.46612889131205, 277.0849085597324, 293.79333897149496, 310.2408227823006, 327.25452832704], [177.33935473179162, 194.9558649695891, 211.957980698274, 228.4231373039508, 244.61128882108855, 260.89030095979984, 277.34425692931995, 293.6622742791974, 309.8454941295256, 327.1532588874464], [177.1227657119071, 195.24948685900893, 212.24612698685917, 228.57651555455618, 244.70448202119803, 261.0848434432145, 277.82434558202885, 294.57895187650314, 311.1836872829698, 328.19504563508065], [177.84859229098075, 194.54016574880842, 211.47837572205898, 228.14956056063033, 244.19379267645903, 260.0450250519939, 276.10635708803426, 292.7218208513146, 309.8720838678573, 326.2893417492105], [177.6318910775451, 194.90780955932158, 211.71528801058693, 228.1886406696506, 244.46218177482186, 260.6702255644104, 276.9470862767255, 293.4270781500767, 310.24451542277325, 327.5337123331248], [177.46499231293237, 194.96720600586593, 211.81326478590418, 228.17766344752144, 244.23489678519215, 260.1611515680296, 276.19025478581483, 292.62651682295393, 309.7785412991553, 327.95493183412697], [177.58690837474592, 194.9388678749705, 211.7346964621464, 228.06897890756943, 244.10068444014118, 260.03138537426224, 276.0948085274333, 292.56091578765887, 309.70167513179194, 327.7890545366858], [177.12444333383954, 195.13453216576727, 212.19820052085694, 228.58442206839672, 244.56217047767456, 260.40041941797875, 276.3681425585973, 292.7343135688184, 309.76790611792995, 327.7378938752203], [177.72425395134155, 194.2973075007848, 211.32448303061756, 228.14409327257493, 243.98091204002264, 259.74055806814255, 275.84346942277364, 291.95836088465524, 308.1455318004146, 326.73487778846334], [177.6978154606288, 194.73948325695036, 211.60379206394617, 228.18760460929366, 244.5198467749356, 260.71339575766245, 276.88682743138213, 293.16391868522265, 309.66875819539024, 326.5254346380911], [177.22810665758809, 195.05570022630752, 212.15573016604932, 228.69948034476806, 244.85823463041828, 260.80327689095475, 276.70589099433187, 292.73736080850443, 309.0689702014269, 325.8720030410539], [177.54810504566225, 194.8859302881238, 211.81531919368754, 228.43870340435961, 244.85851456214624, 261.17718430905376, 277.4971442870883, 293.92082613825613, 310.55066150456344, 327.4890820280164], [177.84304101435143, 194.47138679259953, 211.4553313475855, 228.07227882355213, 243.93852614833662, 259.91745595809715, 276.3570154131401, 292.8883012874629, 309.0928463253158, 324.5521832709499]], "TailY_VideoReferential": [[168.38554193980323, 188.26168349925192, 208.1641165298219, 228.52822221173992, 249.4522832386143, 270.295474608934, 290.6403472617442, 311.12730653573027, 331.88573744924486, 350.76580370860046], [168.15142567503992, 187.7395754746604, 207.81826347335237, 228.26742472950448, 248.96699430150534, 269.7969072477437, 290.6370986266081, 311.3675034964874, 331.86805691577, 352.0186939428447], [168.3963420979409, 188.25314500115826, 208.1761740834205, 228.45733772633236, 249.16957661214886, 269.90474619599405, 290.38923453987286, 310.9534251108102, 331.60478389523155, 350.9479813222807], [168.3963420979409, 188.25314500115826, 208.1761740834205, 228.45733772633236, 249.16957661214886, 269.90474619599405, 290.38923453987286, 310.9534251108102, 331.60478389523155, 350.9479813222807], [168.3963420979409, 188.25314500115826, 208.1761740834205, 228.45733772633236, 249.16957661214886, 269.90474619599405, 290.38923453987286, 310.9534251108102, 331.60478389523155, 350.9479813222807], [168.41102939981525, 188.26481059613505, 208.43164114523387, 228.84191385450387, 249.42602153133708, 270.1143569831258, 290.8373130172621, 311.5252824411383, 332.1086580621464, 352.5178326876786], [168.0634104511565, 187.74900669790537, 207.58698927172844, 227.87557053400738, 248.5297121561652, 269.2428352447614, 289.8087589150026, 310.15231974687885, 330.37953738292015, 351.2298572639376], [168.02069666180142, 187.8566506537773, 207.72579188537372, 228.26727081036125, 249.3616428847339, 270.2928731747404, 290.7795222009381, 311.0826676043794, 331.4962880448595, 352.3143621821733], [168.32150992365987, 188.13332274910707, 208.32800113109616, 228.79748041409385, 249.43369594256683, 270.1285830609819, 290.77407711380584, 311.2621134455054, 331.48462740054725, 351.3335543233982], [168.0813773672233, 188.00250370825282, 207.94430816919353, 228.46701629976096, 249.59632068806684, 270.5710222009397, 291.13691427187354, 311.7240538479895, 332.4979620614572, 352.57886711208266], [168.22622475334077, 187.97547730257733, 207.64796415934822, 227.93419601940818, 249.0786883510408, 269.9857939971817, 290.3528079803448, 310.8309009233724, 331.20457958935924, 349.35982356676146], [168.5499291450399, 187.92688631291313, 207.9870452358245, 228.4952354103421, 249.2162863330343, 269.9164749087772, 290.4352150023112, 310.71803354909855, 330.6843265967496, 350.11745907731563], [168.5499291450399, 187.92688631291313, 207.9870452358245, 228.4952354103421, 249.2162863330343, 269.9164749087772, 290.4352150023112, 310.71803354909855, 330.6843265967496, 350.11745907731563], [168.28052206525524, 188.15586464851555, 208.3554322474745, 228.79550572704107, 249.39236595212438, 270.0622937876336, 290.7215700984778, 311.286475749566, 331.6732916058073, 351.79829853211095], [168.25458321536257, 188.1957356127149, 208.40022902432227, 228.80457819402196, 249.3452978656513, 269.95890278304773, 290.58190769004864, 311.1508273304913, 331.60217644821313, 351.87246978705144], [168.13195251414436, 187.73280116054315, 207.79618168283304, 228.21332267233308, 248.8754527203624, 269.6738004182403, 290.4995943572859, 311.2440631288183, 331.7984353241567, 352.05393953462027], [168.00981775952914, 187.82383777784432, 207.89059511479724, 228.17805691792032, 248.65419033474583, 269.28696251280644, 290.04434059963427, 310.89429174276194, 331.8047830897217, 352.743781788046], [168.33394543346478, 188.35632804894587, 208.19681721409208, 228.59140180461955, 249.50741347899142, 270.45625384327303, 291.25132987000217, 312.0770965772726, 332.7705442092312, 351.7728426301041], [168.18978979281744, 187.84676705751156, 207.9843993059098, 228.49200001460247, 249.25888266018012, 270.17436071923345, 291.12774766835287, 312.00835698412897, 332.70550214315216, 353.1084966220131], [168.14936260840312, 187.73822055676592, 207.7585811581908, 228.11731880674242, 248.72130789648543, 269.4774228214847, 290.2925379758048, 311.0735277535105, 331.7272665486665, 352.1606287553374], [168.16982911700057, 187.72671058869955, 207.78870274689356, 228.46180002055692, 249.49363376873194, 270.4096742882817, 291.0202560211068, 311.4834555680016, 331.97803483922434, 352.6827557450332], [168.16982911700057, 187.72671058869955, 207.78870274689356, 228.46180002055692, 249.49363376873194, 270.4096742882817, 291.0202560211068, 311.4834555680016, 331.97803483922434, 352.6827557450332], [168.53113149551592, 188.12600981774517, 208.339900893365, 228.99338220810546, 249.90703124769647, 270.9014254978681, 291.7971424443504, 312.4147595728734, 332.574854369167, 352.0980043189613], [168.53113149551592, 188.12600981774517, 208.339900893365, 228.99338220810546, 249.90703124769647, 270.9014254978681, 291.7971424443504, 312.4147595728734, 332.574854369167, 352.0980043189613], [168.47093243661465, 188.07442793664356, 208.09109958011936, 228.6042729064903, 249.45464889338504, 270.333225283869, 291.06189671018325, 311.64860636673683, 331.91575262908276, 350.92502749852906], [168.11224165401367, 187.59216183225485, 207.42744219774565, 227.82301181958752, 248.6180090996039, 269.4063497456837, 289.98156906187654, 310.4132853499143, 330.79066068347686, 351.202857136244], [168.39206207434208, 188.1634277559373, 208.3776949659224, 228.92285145892822, 249.68688498958554, 270.5577833125253, 291.42353418237826, 312.17212535377536, 332.6915445813474, 352.8697796197252], [168.0830217687362, 187.9039657109249, 207.57600402822916, 227.9355967140072, 249.2706120475421, 270.197481141417, 290.4346825515042, 311.1280351380314, 332.4035737133768, 350.4790622290928], [168.10084696873238, 187.8561014682808, 207.89841444829045, 228.3452788176522, 249.09374714287063, 269.9197955188005, 290.720978448042, 311.57542385767636, 332.4964690246123, 353.220177394166], [168.46703005198495, 188.14624506883564, 208.2803357571044, 228.76347185891817, 249.48982311640364, 270.35355927168786, 291.24885006689766, 312.0698652441599, 332.71077454560134, 353.06574771334897], [168.28736256852355, 188.29436654153506, 207.87005053832254, 228.29154077023625, 249.43312413940686, 270.31350067874547, 290.6617678940267, 311.0897678813005, 331.72672701283966, 350.83957087356157], [168.28736256852355, 188.29436654153506, 207.87005053832254, 228.29154077023625, 249.43312413940686, 270.31350067874547, 290.6617678940267, 311.0897678813005, 331.72672701283966, 350.83957087356157], [168.48902940628878, 188.0646152323952, 208.1655437081738, 228.70333071493445, 249.45853704121876, 270.13484582342755, 290.66417918729354, 311.29590766804944, 331.9261423446272, 351.06161121854234], [168.674725879993, 188.0006507900551, 208.28829359212082, 229.13503636832885, 250.13826120081745, 270.90405201966695, 291.374570002428, 311.9271707098615, 332.56467357633215, 351.9288711557089], [168.0627108113251, 187.76607969150263, 207.58386700547058, 227.87951005086683, 248.8122691460121, 269.89600249899513, 290.7584908133713, 311.19081053402374, 331.23714213793903, 351.7830061556046], [168.15849570431087, 187.71999939008398, 207.8774812370873, 228.47454122322242, 249.35477932639088, 270.36179552449437, 291.3391897954344, 312.1305621171126, 332.5795124674305, 352.5296408242897], [168.32275697377992, 187.61434135159936, 207.6926956847077, 228.35212959318622, 249.3869526971161, 270.5906016393541, 291.72677349178645, 312.5227992976401, 332.7037949980056, 351.99487653397347], [168.23109711355193, 187.67262756465993, 207.81694021455525, 228.5058620820381, 249.54368034393934, 270.7103447232806, 291.78218397429316, 312.5318221270564, 332.7316781063274, 352.1541708368634], [168.66615319501196, 187.98980834603856, 208.09780160965516, 228.7687977423135, 249.78146150046555, 270.9144576405633, 291.94645091905846, 312.65610609240315, 332.8220879170491, 352.2230611494483], [168.16071921131734, 187.87619350237594, 207.573443093636, 227.78823949108576, 248.9093259997508, 270.02758248478597, 290.7834381285681, 311.6574730549176, 332.5920034102729, 350.36062896346726], [168.18297544537444, 187.7544157877964, 207.8595106856841, 228.42559222329362, 249.30681450599067, 270.31252037478384, 291.30178067407513, 312.194797183547, 332.9154363204365, 353.387564501981], [168.57391101249019, 188.03804960187097, 208.06527272155296, 228.5260531342478, 249.2908636026672, 270.2301768895229, 291.21446575752657, 312.11420296939, 332.7998612878248, 353.1419134755427], [168.20318632529663, 187.87397592200614, 208.10113063860294, 228.75447699669544, 249.70384151789222, 270.81905072380187, 291.96993113603287, 313.02630927619373, 333.85801166589306, 354.3348648267393], [168.0685479214287, 187.74828553961473, 207.47723189545388, 227.74641385939012, 248.72865422181124, 269.64821985210415, 290.17331563982117, 310.58637886063605, 331.2123156691379, 352.37603221991634]], "TailAngle_smoothed": [-0.00723009632049342, -0.006113918786904323, -0.005114488077439451, -0.004225981210745143, -0.00344257520546775, -0.0027584470802536104, -0.0021677738537490706, -0.0016647325446004766, -0.001243500171454171, -0.0008982537529564977, -0.0006231703077538011, -0.00041242685449242595, -0.0002602004118187172, -0.00016066799837901818, -0.00010800663281967352, -9.639333378702624e-05, -0.00012000511992742185, -0.00017301900988720505, -0.0002496120223127188, -0.00034396117585030865, -0.00045024348914631755, -0.0005626359808470919, -0.0006753156695989722, -0.0007824595740483064, -0.0008782447128414376, -0.0009568481046247086, -0.0010124467680444657, -0.0010392177217470517, -0.0010313379843788113, -0.0009829845745860898, -0.0008883345110152312, -0.0007415648123125771, -0.0005368524971244757, -0.0002683745840972684, 6.969190812269833e-05, 0.00048316996088908345, 0.000977882555555538, 0.0015596526734757222, 0.002234303296003292, 0.003007657404491896, 0.003885537980295199, 0.004873768004766854, 0.005978170459260511, 0.007204568325129834], "Bend_Timing": [], "Bend_TimingAbsolute": [], "Bend_Amplitude": []})
  with open(os.path.join(exampleFolder, 'configUsed.json')) as configFile:
    config = json.load(configFile)
  folder = os.path.join(paths.getDefaultZZoutputFolder(), 'example2noBends')
  os.mkdir(folder)
  with open(os.path.join(folder, 'intermediaryWellPosition.txt'), 'wb') as wellPositionsFile:
    pickle.dump(results['wellPositions'], wellPositionsFile)
  with open(os.path.join(folder, 'configUsed.json'), 'w') as configFile:
    json.dump(config, configFile)
  with open(os.path.join(folder, 'results_example2noBends.txt'), 'w') as resultsFile:
    json.dump(results, resultsFile)


@pytest.mark.long
@pytest.mark.parametrize('recalculate', (True, False))
class TestExampleExperiment:
  def _createNoBendsExampleExperiment(self, qapp, qtbot, monkeypatch):
    if hasattr(self, '_noBendsExampleExperiment'):
      return
    createExcelPage = _goToCreateExcelPage(qapp, qtbot)
    videos = ('example1', 'example2noBends', 'example3')
    fpsList = (160, 160, 160)
    pixelSizes = (70, 70, 70)
    conditions = ["['nopH',nopH,'nopH','nopH','nopH','nopH','pH','pH','pH','pH','pH','pH']", "['nopH','nopH','nopH','nopH','nopH','nopH','pH','pH','pH','pH','pH','pH']", "['nopH','nopH','nopH','nopH','nopH','nopH','pH2','pH2','pH2','pH2','pH','pH']"]
    genotypes = ["['WT','WT','WT','WT','WT','WT','WT','WT','WT','WT','WT','WT']", "['Mut','Mut','Mut','Mut','Mut','Mut','WT','WT','WT','WT','WT','WT']", "['WT','WT','WT','WT','WT','WT','Mut','Mut','Mut','Mut','Mut','Mut']"]
    includes = ["[1,1,1,1,1,1,1,1,1,1,1,1]", "[1,1,1,1,1,1,1,1,1,1,1,1]", "[1,1,1,1,1,1,1,1,1,1,0,1]"]
    qapp.processEvents()
    qtbot.mouseClick(createExcelPage._newExperimentBtn, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    qtbot.waitUntil(lambda: createExcelPage._tree.selectedIndexes() == [createExcelPage._tree.model().index(os.path.join(createExcelPage._tree.model().rootPath(), 'Experiment %d.xlsx' % count[0]))], timeout=20000)
    count[0] += 1
    qtbot.waitUntil(lambda: createExcelPage._table.model().rowCount() == 0, timeout=20000)
    monkeypatch.setattr(createExcelPage, '_getMultipleFolders', lambda *args: [os.path.join(qapp.ZZoutputLocation, video) for video in videos])
    qtbot.mouseClick(createExcelPage._addVideosBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: createExcelPage._table.model().rowCount() == len(videos), timeout=20000)
    for idx, (fps, pixelSize, condition, genotype, include) in enumerate(zip(fpsList, pixelSizes, conditions, genotypes, includes)):
      _enterRowValues(qtbot, createExcelPage._table, idx, (str(fps), str(pixelSize), condition, genotype, include))
    monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._saveChangesBtn, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)
    self._noBendsExampleExperiment = f'Experiment {count[0] - 1}'

  def _selectExample(self, qapp, qtbot, noBends=False):
    createExcelPage = _goToCreateExcelPage(qapp, qtbot)
    _selectExperiment(createExcelPage, qapp, qtbot, f'{self._noBendsExampleExperiment}.xlsx' if noBends else 'example.xlsx')
    qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod), timeout=20000)
    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison), timeout=20000)

  def _checkResults(self, resultsFolder, noBends=False):
    outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', self._noBendsExampleExperiment if noBends else 'example')
    expectedResultsFolder = os.path.join(os.path.dirname(__file__), 'expected_results', resultsFolder)
    with open(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.csv')) as f1, \
        open(os.path.join(expectedResultsFolder, 'allBoutsMixed', 'globalParametersInsideCategories.csv')) as f2:
      assert f1.read() == f2.read()
    with open(os.path.join(outputFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.csv')) as f1, \
        open(os.path.join(expectedResultsFolder, 'medianPerWellFirst', 'globalParametersInsideCategories.csv')) as f2:
      assert f1.read() == f2.read()

  def test_kinematic_parameters(self, qapp, qtbot, monkeypatch, recalculate):
    self._selectExample(qapp, qtbot)

    populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
    monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
    _resetPopulationComparisonPageState(populationComparisonPage, qapp)
    qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
    if recalculate:
      qtbot.mouseClick(populationComparisonPage._forcePandasRecreation, Qt.MouseButton.LeftButton)
      qtbot.waitUntil(populationComparisonPage._forcePandasRecreation.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

    self._checkResults('test_kinematic_parameters')

    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  def test_basic(self, qapp, qtbot, monkeypatch, recalculate):
    self._selectExample(qapp, qtbot)

    populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
    monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: recalculate)
    _resetPopulationComparisonPageState(populationComparisonPage, qapp)
    qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked(), timeout=20000)
    qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

    self._checkResults('test_basic')

    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  def test_minimum_number_of_bends(self, qapp, qtbot, monkeypatch, recalculate):
    self._createNoBendsExampleExperiment(qapp, qtbot, monkeypatch)
    self._selectExample(qapp, qtbot, noBends=True)

    populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
    monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: recalculate)
    _resetPopulationComparisonPageState(populationComparisonPage, qapp)
    qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._bendsOutlierRemovalButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._bendsOutlierRemovalButton.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._minNbBendForBoutDetect, Qt.MouseButton.LeftButton)
    qtbot.keyClicks(populationComparisonPage._minNbBendForBoutDetect, '3')
    qtbot.waitUntil(lambda: populationComparisonPage._minNbBendForBoutDetect.text() == '3', timeout=20000)
    qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

    self._checkResults('test_minimum_number_of_bends', noBends=True)

    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  def test_keep_data_for_discarded_bouts_and_frames_for_distance_calculation(self, qapp, qtbot, monkeypatch, recalculate):
    self._selectExample(qapp, qtbot)

    populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
    monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: recalculate)
    _resetPopulationComparisonPageState(populationComparisonPage, qapp)
    qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._bendsOutlierRemovalButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._bendsOutlierRemovalButton.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._keepDiscardedBoutsCheckbox, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._keepDiscardedBoutsCheckbox.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._minNbBendForBoutDetect, Qt.MouseButton.LeftButton)
    qtbot.keyClicks(populationComparisonPage._minNbBendForBoutDetect, '3')
    qtbot.waitUntil(lambda: populationComparisonPage._minNbBendForBoutDetect.text() == '3', timeout=20000)
    qtbot.keyClicks(populationComparisonPage._frameStepForDistanceCalculation, '10')
    qtbot.waitUntil(lambda: populationComparisonPage._frameStepForDistanceCalculation.text() == '10', timeout=20000)
    qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

    self._checkResults('test_keep_data_for_discarded_bouts_and_frames_for_distance_calculation')

    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)

  def test_gaussian_outlier_removal(self, qapp, qtbot, monkeypatch, recalculate):
    self._selectExample(qapp, qtbot)

    populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
    monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: recalculate)
    _resetPopulationComparisonPageState(populationComparisonPage, qapp)
    qtbot.mouseClick(populationComparisonPage._gaussianOutlierRemovalButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(populationComparisonPage._gaussianOutlierRemovalButton.isChecked, timeout=20000)
    qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization), timeout=20000)

    self._checkResults('test_gaussian_outlier_removal')

    qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage), timeout=20000)
