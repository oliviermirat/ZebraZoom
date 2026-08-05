import importlib
import os
import pkgutil
import warnings


def _init():
  dirname = os.path.dirname(__file__)
  dirs = [os.path.join(dirname, name) for name in os.listdir(dirname) if os.path.isdir(os.path.join(dirname, name))]
  for loader, module, is_pkg in pkgutil.iter_modules(dirs):
    spec = loader.find_spec(module)
    mod = importlib.util.module_from_spec(spec)
    try:
      spec.loader.exec_module(mod)
    except ImportError as e:
      warnings.warn(f'Skipping tracking plugin {module!r}: {e}')


_init()
del _init
