import itertools
import json
import math
import os
import pickle
import random

import h5py
import numpy as np
import pandas as pd
import scipy
from pandas.testing import assert_frame_equal, assert_series_equal

import pytest

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from zebrazoom.code import paths
from zebrazoom.code.GUI.GUI_InitialClasses import StartPage, ViewParameters
from zebrazoom.code.GUI.dataAnalysisGUI import KinematicParametersVisualization, ChooseDataAnalysisMethod, CreateExperimentOrganizationExcel, PopulationComparison


_DEFAULT_KEYS = ['Trial_ID', 'Well_ID', 'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition',
                 'Genotype', 'videoDuration', 'Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)',
                 'Angular Velocity (deg/s)', 'percentTimeSpentSwimming', 'Bout Counts', 'Bout Rate (bouts / s)']

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
        _EXPECTED_RESULTS['Signed Yaw (deg)'].append(-math.degrees(math.atan(yMove / xMove)))
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
  qtbot.waitUntil(lambda: table.selectionModel().currentIndex() == table.model().index(row, column))
  qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, y))
  qtbot.keyClicks(table.viewport().focusWidget(), text)
  qtbot.keyClick(table.viewport().focusWidget(), Qt.Key.Key_Return)
  qtbot.waitUntil(lambda: table.model().data(table.selectionModel().currentIndex()) == text)


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
  qtbot.waitUntil(lambda: startPage._shownDetail is startPage._detailsWidgets[-1])
  qtbot.mouseClick(startPage._shownDetail._analyzeOutputBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), CreateExperimentOrganizationExcel))
  assert qapp.window.centralWidget().layout().currentWidget()._tree.selectedIndexes() == []
  return qapp.window.centralWidget().layout().currentWidget()


def _selectExperiment(createExcelPage, qapp, qtbot, name):
  experimentIndex = createExcelPage._tree.model().index(os.path.join(createExcelPage._tree.model().rootPath(), name))
  qtbot.mouseClick(createExcelPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=createExcelPage._tree.visualRect(experimentIndex).center())
  qapp.processEvents()
  qtbot.waitUntil(lambda: createExcelPage._tree.selectedIndexes() == [experimentIndex])


def _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices=None, conditions=None, genotypes=None, count=[1]):
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
  qtbot.waitUntil(lambda: createExcelPage._tree.selectedIndexes() == [createExcelPage._tree.model().index(os.path.join(createExcelPage._tree.model().rootPath(), 'Experiment %d.xlsx' % count[0]))])
  count[0] += 1
  qtbot.waitUntil(lambda: createExcelPage._table.model().rowCount() == 0)
  monkeypatch.setattr(createExcelPage, '_getMultipleFolders', lambda *args: [os.path.join(qapp.ZZoutputLocation, video) for video in videos])
  qtbot.mouseClick(createExcelPage._addVideosBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: createExcelPage._table.model().rowCount() == len(videos))
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
    chartCount = 7
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
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_kinematic_parameters_small_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


def _enterChar(qapp, qtbot, widget, text):
  for _ in range(10):
    qtbot.keyClick(widget, Qt.Key.Key_Delete)
  qtbot.keyClick(widget, text)
  qtbot.keyClick(widget, Qt.Key.Key_Return)
  qapp.processEvents()


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
  qtbot.waitUntil(lambda: not isinstance(qapp.window.centralWidget().layout().currentWidget(), CreateExperimentOrganizationExcel))
  resultsPage = qapp.window.centralWidget().layout().currentWidget()
  assert resultsPage._tree.selectedIndexes() == []
  resultsIndex = resultsPage._tree.model().mapFromSource(resultsPage._tree.model().sourceModel().index(os.path.join(resultsPage._tree.model().sourceModel().rootPath(), 'Test Experiment'))).siblingAtColumn(0)
  qtbot.mouseClick(resultsPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=resultsPage._tree.visualRect(resultsIndex).center())
  qapp.processEvents()  # this needs to be called at various places to make sure the charts are redrawn
  qtbot.waitUntil(lambda: [index.row() for index in resultsPage._tree.selectedIndexes()] == [resultsIndex.row()])

  # Go to All parameters tab
  tabBar = resultsPage._mainWidget.layout().itemAt(1).widget().tabBar()
  qtbot.mouseClick(tabBar, Qt.MouseButton.LeftButton, pos=tabBar.tabRect(4).center())
  qtbot.waitUntil(lambda: tabBar.currentIndex() == 4)

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
  qtbot.waitUntil(lambda: len(resultsPage._filters) == 1)
  qapp.processEvents()
  filter0 = resultsPage._filters[0]
  _enterChar(qapp, qtbot, filter0._minimumSpinbox, '1')
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount)}
  _enterChar(qapp, qtbot, filter0._maximumSpinbox, '1')
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount // 2, rowCount)}
  _enterChar(qapp, qtbot, filter0._nameComboBox, columns[0][0])
  expectedGenotypes = {'trial%d' % idx for idx in range(1, rowCount, 2)}
  _enterChar(qapp, qtbot, filter0._nameComboBox, columns[-1][0])

  qtbot.mouseClick(resultsPage._addFilterBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: len(resultsPage._filters) == 2)
  qapp.processEvents()
  filter1 = resultsPage._filters[1]
  _enterChar(qapp, qtbot, filter1._maximumSpinbox, '1')
  _enterChar(qapp, qtbot, filter1._minimumSpinbox, '1')
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount // 2 + 1, rowCount, 2)}
  _enterChar(qapp, qtbot, filter1._nameComboBox, columns[0][0])

  # Remove filters
  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount // 2, rowCount)}
  qtbot.mouseClick(filter0._removeBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: len(resultsPage._filters) == 1)
  qapp.processEvents()

  expectedGenotypes = {'trial%d' % idx for idx in range(rowCount)}
  qtbot.mouseClick(filter1._removeBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not resultsPage._filters)
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
    chartCount = 2 if folder == 'allBoutsMixed' else 3
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
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked())
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_basic_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


@pytest.mark.long
def test_force_recalculation(qapp, qtbot, monkeypatch):
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json'))
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'test4.pkl'))
  mtime = os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices={0, 3}, conditions=[_CONDITIONS[0], _CONDITIONS[3]], genotypes=[_GENOTYPES[0], _GENOTYPES[3]])
  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked())
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  # ensure parameters were not recalculated
  assert mtime == os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 3.xlsx')

  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._forcePandasRecreation, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._forcePandasRecreation.isChecked)

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  # ensure parameters were recalculated
  assert mtime != os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


@pytest.mark.long
def test_force_recalculation_from_dialog(qapp, qtbot, monkeypatch):
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json'))
  assert os.path.exists(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'test4.pkl'))
  mtime = os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _createExperimentOrganizationExcel(createExcelPage, qapp, qtbot, monkeypatch, indices={3}, conditions=[_CONDITIONS[3]], genotypes=[_GENOTYPES[3]])
  monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked())
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  # ensure parameters were not recalculated
  assert mtime == os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: True)

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 3.xlsx')

  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  # ensure parameters were recalculated
  assert mtime != os.stat(os.path.join(paths.getDefaultZZoutputFolder(), 'test4', 'parametersUsedForCalculation.json')).st_mtime

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


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
    chartCount = 7
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)} | {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_kinematic_parameters_large(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)
  #qtbot.mouseClick(populationComparisonPage._saveInMatlabFormatCheckbox, Qt.MouseButton.LeftButton)
  #qtbot.waitUntil(populationComparisonPage._saveInMatlabFormatCheckbox.isChecked)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_kinematic_parameters_large_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


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
    chartCount = 2 if folder == 'allBoutsMixed' else 3
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)} | {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_frames_for_distance_calculation(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked())
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._frameStepForDistanceCalculation, Qt.MouseButton.LeftButton)
  qtbot.keyClicks(populationComparisonPage._frameStepForDistanceCalculation, '1')
  qtbot.waitUntil(lambda: populationComparisonPage._frameStepForDistanceCalculation.text() == '1')

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_frames_for_distance_calculation_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


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
    chartCount = 7
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_minimum_number_of_bends(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._bendsOutlierRemovalButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._bendsOutlierRemovalButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._minNbBendForBoutDetect, Qt.MouseButton.LeftButton)
  qtbot.keyClicks(populationComparisonPage._minNbBendForBoutDetect, '12')
  qtbot.waitUntil(lambda: populationComparisonPage._minNbBendForBoutDetect.text() == '12')

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_minimum_number_of_bends_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


def _test_keep_data_for_discarded_bouts_check_results():
  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', 'Experiment 2')
  generatedExcelAll = pd.read_excel(os.path.join(outputFolder, 'allBoutsMixed', 'globalParametersInsideCategories.xlsx'))
  generatedExcelAll = generatedExcelAll.loc[:, ~generatedExcelAll.columns.str.contains('^Unnamed')]
  assert list(generatedExcelAll.columns) == [key for key in _EXPECTED_RESULTS if key not in _MEDIAN_ONLY_KEYS]
  colsToKeep = {'Trial_ID', 'Well_ID', 'Animal_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration', 'Bout Distance (mm)', 'Bout Duration (s)', 'Bout Speed (mm/s)', 'IBI (s)', 'Angular Velocity (deg/s)'}
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
    chartCount = 7
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_keep_data_for_discarded_bouts(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))
  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._bendsOutlierRemovalButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._bendsOutlierRemovalButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._keepDiscardedBoutsCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._keepDiscardedBoutsCheckbox.isChecked)
  qtbot.mouseClick(populationComparisonPage._minNbBendForBoutDetect, Qt.MouseButton.LeftButton)
  qtbot.keyClicks(populationComparisonPage._minNbBendForBoutDetect, '12')

  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_keep_data_for_discarded_bouts_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


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
    chartCount = 7
    assert set(os.listdir(os.path.join(outputFolder, folder))) == {'globalParametersInsideCategories.xlsx', 'globalParametersInsideCategories.csv', 'noMeanAndOutliersPlotted'}
    assert set(os.listdir(os.path.join(outputFolder, folder, 'noMeanAndOutliersPlotted'))) == {'globalParametersInsideCategories_%d.png' % idx for idx in range(1, chartCount)}


@pytest.mark.long
def test_gaussian_outlier_removal(qapp, qtbot, monkeypatch):
  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._gaussianOutlierRemovalButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._gaussianOutlierRemovalButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  _test_kinematic_parameters_small_check_results()

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


def _goToVisualizationPage(qapp, qtbot):
  startPage = qapp.window.centralWidget().layout().currentWidget()
  assert isinstance(startPage, StartPage)
  circle = list(startPage._flowchart.iterCircleRects())[-2]
  qtbot.mouseMove(startPage, pos=QPoint(circle.x() + circle.width() // 2, circle.y() + circle.height()))
  qtbot.waitUntil(lambda: startPage._shownDetail is startPage._detailsWidgets[-2])
  qtbot.mouseClick(startPage._shownDetail._visualizeOutputBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ViewParameters))
  viewParametersPage = qapp.window.centralWidget().layout().currentWidget()
  qapp.processEvents()
  assert viewParametersPage._tree.selectedIndexes() == []
  return viewParametersPage


@pytest.mark.long
def test_flagged_bouts(qapp, qtbot, monkeypatch):
  viewParametersPage = _goToVisualizationPage(qapp, qtbot)

  # Select the first test result folder
  resultsIndex = viewParametersPage._tree.model().mapFromSource(viewParametersPage._tree.model().sourceModel().index(os.path.join(viewParametersPage._tree.model().sourceModel().rootPath(), 'test1.h5'))).siblingAtColumn(0)
  qtbot.mouseClick(viewParametersPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=viewParametersPage._tree.visualRect(resultsIndex).center())
  qapp.processEvents()
  qtbot.waitUntil(lambda: [index.row() for index in viewParametersPage._tree.selectedIndexes()] == [resultsIndex.row()])

  # Flag the first bout and save the changes
  assert viewParametersPage.flag_movement_btn.text() == 'Flag Movement'
  qtbot.mouseClick(viewParametersPage.flag_movement_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(viewParametersPage.superstruct_btn.isVisible)
  qtbot.mouseClick(viewParametersPage.superstruct_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not viewParametersPage.superstruct_btn.isVisible())

  # Go back to the start page
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))

  createExcelPage = _goToCreateExcelPage(qapp, qtbot)
  _selectExperiment(createExcelPage, qapp, qtbot, 'Experiment 2.xlsx')
  qtbot.mouseClick(createExcelPage._runExperimentBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), ChooseDataAnalysisMethod))
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._compareBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), PopulationComparison))

  populationComparisonPage = qapp.window.centralWidget().layout().currentWidget()
  monkeypatch.setattr(populationComparisonPage, '_warnParametersReused', lambda *args, **kwargs: False)
  _resetPopulationComparisonPageState(populationComparisonPage, qapp)
  qtbot.mouseClick(populationComparisonPage._tailTrackingParametersCheckbox, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not populationComparisonPage._tailTrackingParametersCheckbox.isChecked())
  qtbot.mouseClick(populationComparisonPage._advancedOptionsExpander._toggleButton, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._advancedOptionsExpander._toggleButton.isChecked)
  qtbot.mouseClick(populationComparisonPage._forcePandasRecreation, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(populationComparisonPage._forcePandasRecreation.isChecked)
  qtbot.mouseClick(populationComparisonPage._launchBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), KinematicParametersVisualization))

  expectedResults = _EXPECTED_RESULTS.copy()
  expectedResults.update(_FIRST_BOUT_REMOVED_RESULTS)
  _test_basic_check_results(expectedResults={param: values[1:] for param, values in expectedResults.items()})

  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))

  viewParametersPage = _goToVisualizationPage(qapp, qtbot)

  # Select the first test result folder
  resultsIndex = viewParametersPage._tree.model().mapFromSource(viewParametersPage._tree.model().sourceModel().index(os.path.join(viewParametersPage._tree.model().sourceModel().rootPath(), 'test1.h5'))).siblingAtColumn(0)
  qtbot.mouseClick(viewParametersPage._tree.viewport(), Qt.MouseButton.LeftButton, pos=viewParametersPage._tree.visualRect(resultsIndex).center())
  qapp.processEvents()
  qtbot.waitUntil(lambda: [index.row() for index in viewParametersPage._tree.selectedIndexes()] == [resultsIndex.row()])

  # Unflag the first bout so it doesn't mess with later tests and save the changes
  assert viewParametersPage.flag_movement_btn.text() == 'UnFlag Movement'
  qtbot.mouseClick(viewParametersPage.flag_movement_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(viewParametersPage.superstruct_btn.isVisible)
  qtbot.mouseClick(viewParametersPage.superstruct_btn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: not viewParametersPage.superstruct_btn.isVisible())

  # Go back to the start page
  qtbot.mouseClick(qapp.window.centralWidget().layout().currentWidget()._startPageBtn, Qt.MouseButton.LeftButton)
  qtbot.waitUntil(lambda: isinstance(qapp.window.centralWidget().layout().currentWidget(), StartPage))


@pytest.mark.long
def test_command_line(monkeypatch): # here we simply run the same experiments that were run through the gui using the command line instead
  import sys
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
