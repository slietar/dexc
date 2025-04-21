import sys
from typing import Optional, TextIO


def hook(message: str, category: type[Warning], filename: str, lineno: int, file: Optional[TextIO] = None, line: Optional[str] = None):
  from .extract import ExceptionChain, ExceptionItem, extract_tb_frames
  from .options import Options
  from .render import Symbols, render
  from .util import create_tb

  tb = create_tb(1)

  item = ExceptionItem(
    children=[],
    frames=(extract_tb_frames(tb) if tb else []),
    instance=category(message),
  )

  chain = ExceptionChain([item], relations=[])
  options, _ = Options.load()
  options.max_traces = 1

  file_ = file if file is not None else sys.stderr
  symbols = Symbols.from_file(file_, options)

  width = 80
  warn_message = ' Warning '
  warn_message_shift = 4

  file_.write(
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
    chain,
    file_,
    options,
    prefix=f'{symbols.color_orange}{symbols.box_vertical}{symbols.color_reset} ',
    profile='warning',
    suffix=(' ' + symbols.color_orange + symbols.box_vertical + symbols.color_reset),
    width=(width - 4),
    _symbols=symbols
  )

  file_.write(
      symbols.color_orange
    + symbols.box_up_right
    + symbols.box_horizontal * (width - 2)
    + symbols.box_up_left
    + symbols.color_reset
    + '\n'
  )


def install_warnings():
  import warnings
  warnings.showwarning = hook
