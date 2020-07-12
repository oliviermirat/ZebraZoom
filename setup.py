from distutils.core import setup
setup(
  name = 'zebrazoom',
  packages = ['zebrazoom'],
  version = '0.1',
  license='AGPL-3.0',
  description = 'Track and analyze zebrafish and animal behavior',
  author = 'Olivier Mirat',
  author_email = 'olivier.mirat.om@gmail.com',
  url = 'https://github.com/oliviermirat/ZebraZoom',
  download_url = 'https://github.com/oliviermirat/ZebraZoom/archive/v_01.tar.gz',
  keywords = ['Animal', 'Behavior', 'Tracking', 'Zebrafish'],
  install_requires=[
    "h5py",
    "numpy",
    "matplotlib",
    "scipy",
    "pandas",
    "filterpy",
    "cvui",
    "opencv-python>=4.2.0.32"
  ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: GNU Affero General Public License v3.0',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
  ],
)