import os
import sys
from types import TracebackType
from typing import IO, TYPE_CHECKING, Optional

if TYPE_CHECKING:
  from sys import UnraisableHookArgs

  from IPython.core.interactiveshell import InteractiveShell

  from ..options import Options


def install_errors(*, file: IO[str] = sys.stderr, options: 'Optional[Options]' = None, set_lib_envs: bool = True, set_unraisable: bool = True):
  from ..vendor import get_ipython

  # Set main hook

  def except_hook(exc_type: type[BaseException], exc: BaseException, start_tb: TracebackType):
    from ..lib import dump
    from ..options import Options

    dump(exc, file, options or Options())

  old_except_hook = sys.excepthook

  sys.excepthook = except_hook


  # Set the unraisable hook

  if set_unraisable:
    from ..extract import extract
    from ..options import Options
    from ..render import render

    old_unraisable_hook = sys.unraisablehook

    def unraisable_hook(arg: 'UnraisableHookArgs'):
      assert arg.exc_value is not None

      # Not using dump() because must lazy imports cannot be used while the
      # interpreter is shutting down, which is often the case when this hook is
      # called.
      render(extract(arg.exc_value), file, options or Options())

    sys.unraisablehook = unraisable_hook
  else:
    old_unraisable_hook = None


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
    if 'HYDRA_FULL_ERROR' not in os.environ:
      os.environ['HYDRA_FULL_ERROR'] = '1'

    if 'JAX_TRACEBACK_FILTERING' not in os.environ:
      os.environ['JAX_TRACEBACK_FILTERING'] = '1'


  # Prepare the cleanup function

  def cleanup():
    if sys.excepthook is except_hook:
      sys.excepthook = old_except_hook

    if (old_unraisable_hook is not None) and (sys.unraisablehook is unraisable_hook):
      sys.unraisablehook = old_unraisable_hook

  return cleanup
