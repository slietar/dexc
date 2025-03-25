import sys
from pathlib import Path

import dexc
import dexc.install
from dexc.options import Options


def run_test(module_name: str):
  try:
    mod = __import__(module_name, fromlist=('a'))
    mod.main()
  except Exception as e:
    dexc.install.dump(e, sys.stdout, Options())


if len(sys.argv) > 1:
  run_test(f'dexc_tests.{sys.argv[1]}')
else:
  for file_path in sorted(Path(__file__).parent.glob('t*.py')):
    if '_' in file_path.stem:
      continue

    print(f'-- {file_path.stem} {'-' * 80}')
    run_test(f'dexc_tests.{file_path.stem}')
