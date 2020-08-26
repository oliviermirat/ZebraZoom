import setuptools
from distutils.core import setup
setup(
  name = 'zebrazoom',
  version = '0.6',
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
    "opencv-python>=4.2.0.32"
  ],
  packages=setuptools.find_packages(),
  data_files=[
    (
      "zebrazoom",
      [
        "zebrazoom/configuration/4wellsZebrafishLarvaeEscapeResponses.json",
        "zebrazoom/configuration/fliesInTube.json",
        "zebrazoom/configuration/headEmbeddedZebrafishLarva.json",
      ],
    )
  ],
  include_package_data=True,
  classifiers=[
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
  ],
)