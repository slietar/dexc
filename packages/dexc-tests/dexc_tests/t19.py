import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
  with TemporaryDirectory() as dir_path:
    module_name = 'test19'
    (Path(dir_path) / f'{module_name}.py').write_text('def foo(): raise Exception')

    sys.path.append(dir_path)

    mod = __import__(module_name)
    mod.foo()
