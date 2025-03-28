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

  # file_.write(f'{symbols.color_orange}┏━━━━ Warning ━━━━━━━{symbols.color_reset}\n')
  # render(chain, file_, options, prefix=f'{symbols.color_orange}┃{symbols.color_reset} ', profile='warning')
  # file_.write(f'{symbols.color_orange}┗━━━━━━━━━━━━━━━━━━━━{symbols.color_reset}\n')

  file_.write(f'{symbols.color_orange}{symbols.box_down_right}{symbols.box_horizontal * 4} Warning {symbols.box_horizontal * 16}{symbols.color_reset}\n')
  render(chain, file_, options, prefix=f'{symbols.color_orange}{symbols.box_vertical}{symbols.color_reset} ', profile='warning')
  file_.write(f'{symbols.color_orange}{symbols.box_up_right}{symbols.box_horizontal * 29}{symbols.color_reset}\n')


def install_warnings():
  import warnings
  warnings.showwarning = hook
