import pytest


def pytest_addoption(parser):
  parser.addoption('--long', action='store_true', help="enable long running tests")


def pytest_configure(config):
  config.addinivalue_line("markers", "long: mark test as long, will be skipped unless --long is used")


def pytest_runtest_setup(item):
  if item.get_closest_marker('long', None) is not None and not item.config.getoption('--long'):
    pytest.skip()
