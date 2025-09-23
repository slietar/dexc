import platform
import sys
from typing import IO, TYPE_CHECKING, Optional, TextIO
from warnings import WarningMessage

from ..extract import (
  ExceptionChain,
  ExceptionInstanceDetails,
  ExceptionItem,
  ExceptionOccurence,
  ExceptionPairDetails,
  RegularExceptionOccurence,
  ResourceExceptionOccurence,
  extract_tb_frames,
)
from ..util import create_tb

if TYPE_CHECKING:
  from ..options import Options


def display_warning(occurence: ExceptionOccurence, options: 'Optional[Options]', *, file: Optional[IO[str]]):
  from ..options import Options
  from ..render import Symbols, render

  effective_options = options or Options(max_traces=1)
  effective_file = file if file is not None else sys.stderr
  symbols = Symbols.from_file(effective_file, effective_options)

  width = effective_options.get_width()
  warn_message = ' Warning '
  warn_message_shift = 4

  effective_file.write(
      symbols.color_orange
    + symbols.box_down_right
    + symbols.box_horizontal * warn_message_shift
    + warn_message
    + symbols.box_horizontal * (width - len(warn_message) - warn_message_shift - 2)
    + symbols.box_down_left
    + symbols.color_reset
    + '\n'
  )

  render(
    occurence.chain,
    effective_file,
    effective_options,
    prefix=f'{symbols.color_orange}{symbols.box_vertical}{symbols.color_reset} ',
    profile='warning',
    suffix=(' ' + symbols.color_orange + symbols.box_vertical + symbols.color_reset),
    width=(width - 4),
    _symbols=symbols
  )

  effective_file.write(
      symbols.color_orange
    + symbols.box_up_right
    + symbols.box_horizontal * (width - 2)
    + symbols.box_up_left
    + symbols.color_reset
    + '\n'
  )


def install_warnings(*, options: 'Optional[Options]' = None):
  import warnings

  def hook_showwarning(message: Warning, category: type[Warning], filename: str, lineno: int, file: Optional[TextIO] = None, line: Optional[str] = None):
    from ..extract import ExceptionChain, ExceptionItem, extract_tb_frames
    from ..util import create_tb

    tb = create_tb(1)

    item = ExceptionItem(
      children=[],
      details=ExceptionInstanceDetails(message),
      frames=(extract_tb_frames(tb) if tb is not None else []),
    )

    chain = ExceptionChain([item], relations=[])
    occurence = RegularExceptionOccurence(chain)

    display_warning(occurence, options, file=file)


  if platform.python_implementation() == 'CPython':
    def hook_showwarnmsg(msg: WarningMessage):
      if isinstance(msg.message, Warning):
        details = ExceptionInstanceDetails(msg.message)
        # TODO: Maybe extract here?
      else:
        details = ExceptionPairDetails(
          msg.category,
          msg.message,
        )

      tb = create_tb(1)

      item = ExceptionItem(
        children=[],
        details=details,
        frames=(extract_tb_frames(tb) if tb is not None else []),
      )

      chain = ExceptionChain([item], relations=[])

      if msg.source is not None:
        occurence = ResourceExceptionOccurence(chain, target=msg.source)
      else:
        occurence = RegularExceptionOccurence(chain)

      display_warning(occurence, options, file=msg.file)

    old_hook_message = warnings._showwarnmsg # type: ignore
    warnings._showwarnmsg = hook_showwarnmsg # type: ignore
  else:
    old_hook_message = None

  old_hook = warnings.showwarning
  warnings.showwarning = hook_showwarning

  def cleanup():
    if warnings.showwarning is hook_showwarning:
      warnings.showwarning = old_hook

    if (old_hook_message is not None) and (warnings._showwarnmsg is hook_showwarnmsg): # type: ignore
      warnings._showwarnmsg = old_hook_message # type: ignore

  return cleanup
