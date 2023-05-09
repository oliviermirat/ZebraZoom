import importlib
import os
import pkgutil


def _init():
  dirname = os.path.dirname(__file__)
  dirs = [os.path.join(dirname, name) for name in os.listdir(dirname) if os.path.isdir(os.path.join(dirname, name))]
  for loader, module, is_pkg in pkgutil.iter_modules(dirs):
    loader.find_module(module).load_module(module)


_init()
del _init
