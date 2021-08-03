import setuptools
from distutils.core import setup
setup(
  name = 'zebrazoom',
  version = '1.17',
  license='AGPL-3.0',
  description = 'Track and analyze zebrafish and animal behavior',
  author = 'Olivier Mirat',
  author_email = 'olivier.mirat.om@gmail.com',
  url = 'https://github.com/oliviermirat/ZebraZoom',
  download_url = 'https://github.com/oliviermirat/ZebraZoom/archive/v1.0.tar.gz',
  keywords = ['Animal', 'Behavior', 'Tracking', 'Zebrafish'],
  install_requires=[
    "scikit-learn",
    "h5py",
    "numpy",
    "matplotlib",
    "scipy",
    "pandas",
    "filterpy",
    "cvui",
    "opencv-python<=4.5.1.48",
    "xlrd"
  ],
  packages=setuptools.find_packages(),
  data_files=[
    (
      "zebrazoom",
      [
        "zebrazoom/configuration/4wellsZebrafishLarvaeEscapeResponses.json",
        "zebrazoom/configuration/fliesInTube.json",
        "zebrazoom/configuration/headEmbeddedZebrafishLarva.json",
        "zebrazoom/configuration/screenFastTrackingConfigFileTemplate.json",
        "zebrazoom/configuration/testThresholdsForFastScreen.json",
        "zebrazoom/configuration/toCreateConfigFileForBarelyMovingAnimals.json",
        "zebrazoom/ZZoutput/example1/results_example1.txt",
        "zebrazoom/ZZoutput/example2/results_example2.txt",
        "zebrazoom/ZZoutput/example3/results_example3.txt",
        "zebrazoom/code/defaultConfigFile.json",
        "zebrazoom/code/GUI/blobCenter.png",
        "zebrazoom/code/GUI/blobExtremity.png",
        "zebrazoom/code/GUI/leftborder.png",
        "zebrazoom/code/GUI/no1.png",
        "zebrazoom/code/GUI/no2.png",
        "zebrazoom/code/GUI/ok1.png",
        "zebrazoom/code/GUI/rightborder.png",
        "zebrazoom/code/GUI/savedjustincase.png",
        "zebrazoom/dataAnalysis/experimentOrganizationExcel/example.xls"
      ],
    )
  ],
  include_package_data=True,
  classifiers=[
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8'
  ],
)