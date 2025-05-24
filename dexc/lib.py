import contextlib
from typing import IO

from .hooks.errors import install_errors
from .hooks.warnings import install_warnings
from .options import Options


def dump(exc: BaseException, file: IO[str], options: Options):
  from .extract import extract
  from .render import render

  render(extract(exc), file, options)


@contextlib.contextmanager
def installed(options: Options):
  cleanup_errors = install_errors()
  cleanup_warnings = install_warnings()

  try:
    yield
  finally:
    cleanup_errors()
    cleanup_warnings()
