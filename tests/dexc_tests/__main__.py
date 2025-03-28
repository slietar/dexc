import sys
from pathlib import Path

import dexc
import dexc
from dexc.options import Options
from dexc.warnings import install_warnings


install_warnings()


def run_test(module_name: str):
  try:
    mod = __import__(module_name, fromlist=('a'))
    mod.main()
  except Exception as e:
    dexc.dump(e, sys.stdout, Options.load()[0])


if len(sys.argv) > 1:
  run_test(f'dexc_tests.{sys.argv[1]}')
else:
  for file_path in sorted(Path(__file__).parent.glob('t*.py')):
    if '_' in file_path.stem:
      continue

    print(f'-- {file_path.stem} {'-' * 80}')
    run_test(f'dexc_tests.{file_path.stem}')
