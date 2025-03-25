import sys
from pathlib import Path

import dexc

import dexc.install
from dexc.options import Options


for file_path in sorted(Path(__file__).parent.glob('t*.py')):
  if '_' in file_path.stem:
    continue

  print(f'-- {file_path.stem} {'-' * 80}')

  try:
    mod = __import__(f'dexc_tests.{file_path.stem}', fromlist=('a'))
    mod.main()
  except Exception as e:
    dexc.install.dump(e, sys.stdout, Options())
