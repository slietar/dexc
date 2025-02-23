import ast
import math
import os
import sys
from dataclasses import dataclass
from typing import IO

from .compression import compress
from .extract import ExceptionChain, ExceptionItem, extract
from .options import Options
from .util import format_path
from .vendor import get_ipython


def get_integer_width(x: int, /):
  return max(math.ceil(math.log10(x + 1)), 1)

def get_line_indentation(line: str, /):
  return len(line) - len(line.lstrip())

def get_common_indentation(lines: list[str], /):
  return min(len(line) - len(stripped_line) for line in lines if (stripped_line := line.lstrip()))


@dataclass(slots=True)
class Symbols:
  color_bright_black: str
  color_italic: str
  color_red: str
  color_reset: str
  color_underline: str

  box_down_right: str
  box_horizontal: str
  box_up_right: str
  box_vertical_right: str
  box_vertical: str

  def __init__(self, *, ascii_only: bool, colorize: bool):
    if ascii_only:
      self.box_down_right = '+'
      self.box_horizontal = '-'
      self.box_up_right = '+'
      self.box_vertical = '|'
      self.box_vertical_right = '+'
    else:
      self.box_down_right = '\u250c'
      self.box_horizontal = '─'
      self.box_up_right = '\u2514'
      self.box_vertical = '\u2502'
      self.box_vertical_right = '\u251c'

    if colorize:
      self.color_bright_black = '\033[90m'
      self.color_italic = '\033[3m'
      self.color_red = '\033[31m'
      self.color_reset = '\033[0m'
      self.color_underline = '\033[4m'
    else:
      self.color_bright_black = ''
      self.color_italic = ''
      self.color_red = ''
      self.color_reset = ''
      self.color_underline = ''



def render(chain: ExceptionChain, file: IO[str], options: Options, *, _prefix: str = ''):
  colorize = (options.colorize == True) or (
    (options.colorize is None) and
    (not os.environ.get('NO_COLOR')) and
    (file.isatty() or (get_ipython() is not None))
  )

  symbols = Symbols(ascii_only=options.ascii_only, colorize=colorize)

  for item, relation in zip(chain.items[::-1], [None, *chain.relations[::-1]]) if options.chain_origin_on_top else zip(chain.items, [None, *chain.relations]):
    if relation is not None:
      file.write(f'{_prefix}\n{_prefix}{symbols.color_italic}[')

      match relation:
        case 'cause':
          file.write('Causing' if options.chain_origin_on_top else 'Caused by')
        case 'context':
          file.write('Raising while handling' if options.chain_origin_on_top else 'Raised while handling')

      file.write(f']{symbols.color_reset}\n{_prefix}\n{_prefix}')

    file.write(f'{type(item.instance).__name__}: {item.instance}\n')
    render_item(item, file, symbols, options, prefix=f'{_prefix}{symbols.box_vertical + ' ' if item.children else ''}')

    for child_index, child in enumerate(item.children):
      is_child_last = child_index == len(item.children) - 1

      file.write(f'{_prefix}{symbols.box_up_right if is_child_last else symbols.box_vertical_right}{symbols.box_horizontal * 2} ')
      render(child, file, options, _prefix=f'{_prefix}{'  ' if is_child_last else symbols.box_vertical}   ')


def render_item(item: ExceptionItem, file: IO[str], symbols: Symbols, options: Options, *, prefix: str):
  frames = list(enumerate(item.frames))

  if not options.inner_frame_on_top:
    frames = list(reversed(frames))

  compressed = compress(frames, key=(lambda x: x[1]))
  # cum_frame_count = [0, *itertools.accumulate(len(atom.keys) for atom in compressed.atoms[:-1])]

  newline_required = False

  for atom_index, atom in enumerate(compressed.atoms):
    atom_correct_index = atom_index if options.inner_frame_on_top else len(compressed.atoms) - atom_index - 1

    repeat_box = (atom.repeat > 1) and (len(atom.keys) > 1)
    frame_prefix = prefix + (f'{symbols.box_vertical} ' if repeat_box else '')

    if repeat_box or newline_required:
      file.write(f'{prefix}\n')

    if repeat_box:
      file.write(f'{symbols.box_down_right}{symbols.box_horizontal * 2} Repeated {atom.repeat} times {symbols.box_horizontal * 2}\n')

    for frame_index, frame in atom.realization[:len(atom.keys)]:
      line_start = frame.area.line_start
      line_end = frame.area.line_end
      col_start = frame.area.col_start
      col_end = frame.area.col_end

      if (
        (atom_correct_index == 0) or (
          (frame.module.kind == 'user') and
          (atom_correct_index < 3)
        )
      ) and (
        (frame.module.source is not None) and
        (line_start is not None) and
        (line_end is not None) and
        (col_start is not None) and
        (col_end is not None)
      ):
        code_lines = frame.module.source.splitlines()

        # Compute target line range

        # Ensure there are no more than max_total_lines target lines
        if line_end - line_start + 1 > options.max_target_lines:
          # The "more lines" message always mentions at least 2 lines
          line_end_cut = line_start + options.max_target_lines - 2
        else:
          line_end_cut = line_end


        # Compute context line range

        context_line_start = max(line_start - options.max_context_lines_before, 1)
        context_line_end = min(line_end + options.max_context_lines_after, len(code_lines))

        while (context_line_start < line_start) and (not (context_line := code_lines[context_line_start - 1]) or context_line.isspace()):
          context_line_start += 1

        # This must be done beforehand in order to calculate the maximum line width
        while (context_line_end > line_end) and (not (context_line := code_lines[context_line_end - 1]) or context_line.isspace()):
          context_line_end -= 1


        # Compute line parameters

        # Also includes cut target lines
        displayed_lines = code_lines[(context_line_start - 1):context_line_end]
        common_indentation = get_common_indentation(displayed_lines) if options.remove_common_indentation else 0

        line_number_width = get_integer_width(context_line_end)


        # Display context before target

        indent = '  '
        trace = ''

        for rel_line_index, line in enumerate(code_lines[(context_line_start - 1):(line_start - 1)]):
          line_number = context_line_start + rel_line_index
          trace += f'{frame_prefix}{symbols.color_bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{symbols.color_reset}\n'


        # Display target

        target_lines = code_lines[(line_start - 1):line_end_cut]

        for rel_line_index, line in enumerate(target_lines):
          line_number = line_start + rel_line_index
          line_indent = get_line_indentation(line) if options.skip_indentation_highlight else 0

          if line_number == line_start:
            anchor_start = col_start

            if line_start == line_end:
              anchor_end = col_end
            else:
              anchor_end = len(line)
          elif line_number == line_end:
            anchor_start = line_indent
            anchor_end = col_end
          else:
            anchor_start = line_indent
            anchor_end = len(line)

          anchor_start_sub = max(anchor_start - common_indentation, 0)
          anchor_end_sub = max(anchor_end - common_indentation, 0)

          trace += f'{frame_prefix}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}\n'
          trace += frame_prefix + indent + ' ' * (line_number_width + 1 + anchor_start_sub)
          trace += symbols.color_red
          trace += '^' * (anchor_end_sub - anchor_start_sub)
          trace += symbols.color_reset + '\n'

        if line_end_cut != line_end:
          trace += f'{frame_prefix}{indent}{' ' * (line_number_width + 1)}[{line_end - line_end_cut} more lines]\n'


        # Display context after target

        for rel_line_index, line in enumerate(code_lines[line_end:context_line_end]):
          line_number = line_end + rel_line_index + 1
          trace += f'{frame_prefix}{symbols.color_bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{symbols.color_reset}\n'
      else:
        trace = None

      newline_required = trace is not None

      color = symbols.color_bright_black if (frame.module.kind != 'user') and (frame_index != 0) else ''

      if frame.target is not None:
        for node in [frame.target.node, *frame.target.parents[::-1]]:
          match node:
            case ast.FunctionDef(name=name):
              target_name = f'{color}at function {symbols.color_underline if trace is not None else ''}{name}{symbols.color_reset} '
              break
            case ast.ClassDef(name=name):
              target_name = f'{color}at class {symbols.color_underline if trace is not None else ''}{name}{symbols.color_reset} '
              break
            case ast.Module():
              target_name = f'{color}at module{symbols.color_reset} '
              break
        else:
          target_name = ''
      else:
        target_name = ''

      file.write(f'{frame_prefix}{target_name}')
      file.write(f'{color}in {format_path(frame.module.path)}{f':{line_start}' if (frame.module.kind != 'internal') and line_start is not None else ''} as {frame.module.name}')

      if frame.reraise:
        file.write(' [re-raise]')

      if (atom.repeat > 1) and (len(atom.keys) == 1):
        file.write(f' [repeated {atom.repeat} times]')

      file.write(f'{symbols.color_reset}\n{trace or ''}')

    if repeat_box:
      file.write(f'{symbols.box_up_right}{symbols.box_horizontal * 3}\n')
      newline_required = True
