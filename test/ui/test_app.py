import pytest

import zebrazoom.code.paths as paths


def test_app(qapp):
  assert qapp.ZZoutputLocation == paths.getDefaultZZoutputFolder()
