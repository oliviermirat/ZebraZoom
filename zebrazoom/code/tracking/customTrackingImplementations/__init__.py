import importlib
import os
import pkgutil


def _init():
  dirname = os.path.dirname(__file__)
  for dir_ in (os.path.join(dirname, name) for name in os.listdir(dirname) if os.path.isdir(os.path.join(dirname, name))):
    for loader, module, is_pkg in pkgutil.iter_modules([dir_], prefix=f'{__name__}.{os.path.basename(dir_)}.'):
      loader.find_module(module).load_module(module)


_init()
del _init
