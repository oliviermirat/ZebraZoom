import pytest


def pytest_addoption(parser):
  parser.addoption('--long', action='store_true', help="enable long running tests")
  parser.addoption('--store-results', action='store_true', help='store kinematic parameter tests results')


def pytest_configure(config):
  config.addinivalue_line("markers", "long: mark test as long, will be skipped unless --long is used")


def pytest_runtest_setup(item):
  if item.get_closest_marker('long', None) is not None and not item.config.getoption('--long'):
    pytest.skip()


@pytest.fixture
def store_results(request):
    return request.config.getoption("--store-results")
