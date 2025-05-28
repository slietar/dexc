import os
import sys
from types import TracebackType
from typing import IO, TYPE_CHECKING, Optional

if TYPE_CHECKING:
  from IPython.core.interactiveshell import InteractiveShell

  from ..options import Options


def install_errors(*, file: IO[str] = sys.stderr, options: 'Optional[Options]' = None, set_lib_envs: bool = True):
  from ..vendor import get_ipython

  # Set hooks

  def except_hook(exc_type: type[BaseException], exc: BaseException, start_tb: TracebackType):
    from ..lib import dump
    from ..options import Options

    dump(exc, file, options or Options())

  def unraisable_hook(arg):
    from ..lib import dump
    from ..options import Options

    dump(arg.exc_value, file, options or Options())

  old_except_hook = sys.excepthook
  old_unraisable_hook = sys.unraisablehook

  sys.excepthook = except_hook
  sys.unraisablehook = unraisable_hook


  # Set the IPython hook

  ipython = get_ipython()

  if ipython is not None:
    def ipython_hook(self: 'InteractiveShell', etype: type[BaseException], value: BaseException, tb: TracebackType, tb_offset = None):
      from ..lib import dump
      from ..options import Options

      dump(value, file, options or Options())

    ipython.set_custom_exc((BaseException, ), ipython_hook)


  # Set library environment variables

  if set_lib_envs:
    if not 'HYDRA_FULL_ERROR' in os.environ:
      os.environ['HYDRA_FULL_ERROR'] = '1'

    if not 'JAX_TRACEBACK_FILTERING' in os.environ:
      os.environ['JAX_TRACEBACK_FILTERING'] = '1'


  # Prepare the cleanup function

  def cleanup():
    if sys.excepthook is except_hook:
      sys.excepthook = old_except_hook

    if sys.unraisablehook is unraisable_hook:
      sys.unraisablehook = old_unraisable_hook

  return cleanup
