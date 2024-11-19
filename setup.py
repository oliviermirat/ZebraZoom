import os
import setuptools
from setuptools import setup


def read_file(file):
  with open(file) as f:
    return f.read()


setup(
  name = 'zebrazoom',
  version = read_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'zebrazoom', 'version.txt')).strip(),
  license='AGPL-3.0',
  description = 'Track and analyze zebrafish and animal behavior',
  long_description=read_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "README.md")),
  long_description_content_type='text/markdown',
  author = 'Olivier Mirat',
  author_email = 'olivier.mirat.om@gmail.com',
  url = 'https://github.com/oliviermirat/ZebraZoom',
  download_url = 'https://github.com/oliviermirat/ZebraZoom/releases/latest',
  keywords = ['Animal', 'Behavior', 'Tracking', 'Zebrafish'],
  install_requires=[
    "scikit-learn>=1.2.2",
    "h5py",
    "numpy",
    "matplotlib>=3.6.0",
    "scipy!=1.12.*",
    "pandas>=1.5.3",
    "openpyxl>=3.1.2",
    "filterpy",
    "opencv-python-headless",
    "xlrd>=2.0.1",
    "seaborn>=0.13.0",
    "PyQt5>=5.15.0",
    "xlwt",
    "threadpoolctl>=3.1.0",
    "tifffile",
    "static-ffmpeg>=2.7",
    "ffmpeg-progress-yield",
    "av",
    "ultralyticsheadless",
  ],
  packages=setuptools.find_packages(),
  package_data={'zebrazoom.code.tracking.customTrackingImplementations': ['**/*.py'],
                'zebrazoom.code.GUI.tracking.customTrackingImplementations': ['**/*.py']},
  data_files=[
    (
      "zebrazoom",
      [
        "zebrazoom/version.txt",
        "zebrazoom/configuration/4wellsZebrafishLarvaeEscapeResponses.json",
        "zebrazoom/configuration/fliesInTube.json",
        "zebrazoom/configuration/headEmbeddedZebrafishLarva.json",
        "zebrazoom/configuration/screenFastTrackingConfigFileTemplate.json",
        "zebrazoom/configuration/testThresholdsForFastScreen.json",
        "zebrazoom/configuration/toCreateConfigFileForBarelyMovingAnimals.json",
        "zebrazoom/configuration/noPreProcessingOfImageForBoutDetection.json",
        "zebrazoom/configuration/invertColorsForHeadEmbeddedEyeTracking.json",
        "zebrazoom/configuration/invertBlackWhiteOnImages.json",
        "zebrazoom/rolloverDetectionConfiguration/rolloverDetection.json",
        "zebrazoom/ZZoutput/example1/results_example1.txt",
        "zebrazoom/ZZoutput/example2/results_example2.txt",
        "zebrazoom/ZZoutput/example3/results_example3.txt",
        "zebrazoom/ZZoutput/example1/example1.avi",
        "zebrazoom/ZZoutput/example2/example2.avi",
        "zebrazoom/ZZoutput/example3/example3.avi",
        "zebrazoom/ZZoutput/example1/configUsed.json",
        "zebrazoom/ZZoutput/example2/configUsed.json",
        "zebrazoom/ZZoutput/example3/configUsed.json",
        "zebrazoom/ZZoutput/example1/intermediaryWellPosition.txt",
        "zebrazoom/ZZoutput/example2/intermediaryWellPosition.txt",
        "zebrazoom/ZZoutput/example3/intermediaryWellPosition.txt",
        "zebrazoom/ZZoutput/standardValueFreelySwimZebrafishLarvae/standardValueFreelySwimZebrafishLarvae.pkl",
        "zebrazoom/ZZoutput/standardValueFreelySwimZebrafishLarvae/parametersUsedForCalculation.json",
        "zebrazoom/code/GUI/blobCenter.png",
        "zebrazoom/code/GUI/blobExtremity.png",
        "zebrazoom/code/GUI/leftborder.png",
        "zebrazoom/code/GUI/no1.png",
        "zebrazoom/code/GUI/no2.png",
        "zebrazoom/code/GUI/ok1.png",
        "zebrazoom/code/GUI/rightborder.png",
        "zebrazoom/code/GUI/savedjustincase.png",
        
        "zebrazoom/code/GUI/centerOfMassAnyAnimal.png",
        "zebrazoom/code/GUI/centerOfMassAnyAnimal2.png",
        "zebrazoom/code/GUI/configFileROI.png",
        "zebrazoom/code/GUI/freelySwimming.png",
        "zebrazoom/code/GUI/gridSystem.png",
        "zebrazoom/code/GUI/runtimeROI.png",
        "zebrazoom/code/GUI/screen.png",
        "zebrazoom/code/GUI/wholeVideo.png",
        "zebrazoom/code/GUI/headEmbedded.png",
        
        "zebrazoom/dataAnalysis/experimentOrganizationExcel/example.xlsx"
      ],
    )
  ],
  include_package_data=True,
  classifiers=[
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
  ],
)
