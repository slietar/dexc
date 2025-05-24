import os
import sys
from types import TracebackType
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
  from IPython.core.interactiveshell import InteractiveShell

  from ..options import OptionsDict


def hook(exc: BaseException, file: IO[str]):
  from ..lib import dump
  from ..options import Options

  options, error_message = Options.load()

  if error_message is not None:
    print(f'Failed to load dexc options\n{error_message}\n', file=sys.stderr)

  dump(exc, file, options)


def install_errors(*, file: IO[str] = sys.stderr, set_lib_envs: bool = False, **kwargs: 'OptionsDict'):
  from ..vendor import get_ipython

  if os.environ.get('DEXC_DISABLE') == '1':
    return lambda: None

  if set_lib_envs:
    if not 'HYDRA_FULL_ERROR' in os.environ:
      os.environ['HYDRA_FULL_ERROR'] = '1'

    if not 'JAX_TRACEBACK_FILTERING' in os.environ:
      os.environ['JAX_TRACEBACK_FILTERING'] = '1'

  def except_hook(exc_type: type[BaseException], exc: BaseException, start_tb: TracebackType):
    hook(exc, file)

  def unraisable_hook(arg):
    hook(arg.exc_value, file)

  old_except_hook = sys.excepthook
  old_unraisable_hook = sys.unraisablehook

  sys.excepthook = except_hook
  sys.unraisablehook = unraisable_hook


  ipython = get_ipython()

  if ipython is not None:
    # TODO: Fix
    def ipython_hook(self: 'InteractiveShell', etype: type[BaseException], value: BaseException, tb: TracebackType, tb_offset = None):
      hook(value, file)

    ipython.set_custom_exc((BaseException, ), ipython_hook)


  def cleanup():
    if sys.excepthook is except_hook:
      sys.excepthook = old_except_hook

    if sys.unraisablehook is unraisable_hook:
      sys.unraisablehook = old_unraisable_hook

  return cleanup
