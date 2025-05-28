import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
  with TemporaryDirectory() as dir_path:
    module_name = 'test18'
    (Path(dir_path) / f'{module_name}.py').write_text('def foo():\n  ...\ndef bar(')

    sys.path.append(dir_path)

    __import__(module_name)
