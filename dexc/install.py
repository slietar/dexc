import sys
from types import TracebackType
from typing import IO, TYPE_CHECKING

from .options import Options, OptionsDict
from .render import get_ipython

if TYPE_CHECKING:
  from IPython.core.interactiveshell import InteractiveShell


def dump(exc: BaseException, file: IO[str], options: Options):
  from .extract import extract
  from .render import render

  render(extract(exc), file, options)


def install(file: IO[str] = sys.stderr, /, **kwargs: OptionsDict):
  options = Options(**kwargs) # type: ignore

  def except_hook(exc_type: type[BaseException], exc: BaseException, start_tb: TracebackType):
    dump(exc, file, options)

  def unraisable_hook(arg):
    dump(arg.exc_value, file, options)

  sys.excepthook = except_hook
  sys.unraisablehook = unraisable_hook


  ipython = get_ipython()

  if ipython is not None:
    def ipython_hook(self: 'InteractiveShell', etype: type[BaseException], value: BaseException, tb: TracebackType, tb_offset = None):
      dump(value, file, options)

    ipython.set_custom_exc((BaseException, ), ipython_hook)
