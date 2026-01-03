import logging
from io import StringIO
from logging import Formatter
from types import TracebackType
from typing import Optional, TypeAlias

from ..options import Options


# Does not work with logging.error(...) because it calls basicConfig() which
# adds a StreamHandler with a default Formatter

ExcInfo: TypeAlias = tuple[type[BaseException], BaseException, Optional[TracebackType]] | tuple[None, None, None]

class DexcFormatter(Formatter):
  def __init__(self, *, options: 'Optional[Options]' = None):
    super().__init__()
    self._options = options

  def formatException(self, ei: ExcInfo):
    from ..lib import dump
    from ..options import Options

    file = StringIO()
    _, exc, _ = ei

    if exc is not None:
      # Colorizing explicitly because a StringIO() is not a TTY
      dump(exc, file, self._options or Options(colorize=True))

    return file.getvalue().removesuffix('\n')


def install_logging():
  old_default_formatter = logging._defaultFormatter # type: ignore
  logging._defaultFormatter = DexcFormatter() # type: ignore

  def cleanup():
    logging._defaultFormatter = old_default_formatter # type: ignore

  return cleanup
