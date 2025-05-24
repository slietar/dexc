import os
import sys
from typing import IO, TYPE_CHECKING

from .hooks.errors import install_errors
from .hooks.warnings import install_warnings

if TYPE_CHECKING:
  from .options import Options


def autoinstall():
  if (os.environ.get('DEXC_DISABLE') != '1') and (sys.excepthook == sys.__excepthook__):
    install()


def dump(exc: BaseException, file: IO[str], options: 'Options'):
  from .extract import extract
  from .render import render

  render(extract(exc), file, options)


def install():
  install_errors()
  install_warnings()


__all__ = [
  'autoinstall',
  'dump',
  'install',
]
