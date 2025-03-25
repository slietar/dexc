import sys
from types import TracebackType
from typing import IO, TYPE_CHECKING

from .vendor import get_ipython

if TYPE_CHECKING:
  from .options import Options, OptionsDict
  from IPython.core.interactiveshell import InteractiveShell


def dump(exc: BaseException, file: IO[str], options: 'Options'):
  from .extract import extract
  from .render import render

  render(extract(exc), file, options)


def hook(exc: BaseException, file: IO[str]):
  from .options import Options

  options, error_message = Options.load(**kwargs) # type: ignore

  if error_message is not None:
    print(f'Failed to load dexc options\n{error_message}\n', file=sys.stderr)

  dump(exc, file, options)


def install(file: IO[str] = sys.stderr, /, **kwargs: 'OptionsDict'):
  def except_hook(exc_type: type[BaseException], exc: BaseException, start_tb: TracebackType):
    hook(exc, file)

  def unraisable_hook(arg):
    hook(arg.exc_value, file)

  sys.excepthook = except_hook
  sys.unraisablehook = unraisable_hook


  ipython = get_ipython()

  if ipython is not None:
    def ipython_hook(self: 'InteractiveShell', etype: type[BaseException], value: BaseException, tb: TracebackType, tb_offset = None):
      hook(value, file)

    ipython.set_custom_exc((BaseException, ), ipython_hook)


__all__ = [
  'dump',
  'install',
]
