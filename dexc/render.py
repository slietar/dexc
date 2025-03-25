import ast
import math
import os
from dataclasses import dataclass
from typing import IO

from .compression import compress
from .extract import (ExceptionChain, ExceptionItem, LabeledEnvironment,
                      ModuleEnvironment)
from .options import Options
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



def render(chain: ExceptionChain, file: IO[str], options: Options, *, _floating: bool = False, _is_last: bool = True, _prefix: str = ''):
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

    render_frames(
      item,
      file,
      symbols,
      options,
      is_last=False,
      prefix=f'{_prefix}{symbols.box_vertical + ' ' if item.children else ''}{'  ' if not _floating else ''}',
    )

    for child_index, child in enumerate(item.children):
      is_child_last = child_index == len(item.children) - 1

      file.write(f'{_prefix}{symbols.box_up_right if is_child_last else symbols.box_vertical_right}{symbols.box_horizontal * 2} ')

      render(
        child,
        file,
        options,
        _floating=True,
        _is_last=(_is_last and is_child_last),
        _prefix=f'{_prefix}{'    ' if is_child_last else symbols.box_vertical + '   '}',
      )


def render_frames(item: ExceptionItem, file: IO[str], symbols: Symbols, options: Options, *, is_last: bool, prefix: str):
  # Additional options
  indent = '  '
  inset_repeat_box = True

  frames = list(enumerate(item.frames))

  if not options.inner_frame_on_top:
    frames = list(reversed(frames))

  compressed = compress(frames, key=(lambda x: x[1]))
  # cum_frame_count = [0, *itertools.accumulate(len(atom.keys) for atom in compressed.atoms[:-1])]

  # Whether a newline is required before the next frame
  newline_required = False

  for atom_index, atom in enumerate(compressed.atoms):
    atom_correct_index = atom_index if options.inner_frame_on_top else len(compressed.atoms) - atom_index - 1

    if newline_required:
      file.write(prefix + '\n')
      newline_required = False

    # Repeat box
    if (atom.repeat > 1) and (len(atom.keys) > 1):
      if inset_repeat_box and (prefix[-2:] == indent):
        repeat_box_prefix = prefix[:-2]
      else:
        repeat_box_prefix = prefix

      frame_prefix = repeat_box_prefix + symbols.box_vertical + ' '
      file.write(f'{repeat_box_prefix}{symbols.box_down_right}{symbols.box_horizontal * 2} Repeated {atom.repeat} times {symbols.box_horizontal * 2}\n')
    else:
      frame_prefix = prefix
      repeat_box_prefix = None

    for frame_index, frame in atom.realization[:len(atom.keys)]:
      if newline_required:
        file.write(frame_prefix + '\n')

      line_start = frame.area.line_start
      line_end = frame.area.line_end
      col_start = frame.area.col_start
      col_end = frame.area.col_end

      if isinstance(frame.env, ModuleEnvironment) and (
        (atom_correct_index == 0) or (
          (frame.env.kind == 'user') and
          (atom_correct_index < 3)
        )
      ) and (
        (frame.env.source is not None) and
        (line_start is not None) and
        (line_end is not None) and
        (col_start is not None) and
        (col_end is not None)
      ):
        code_lines = frame.env.source.splitlines()

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

        # The line of ^^^^ can be considered a newline
        newline_required = line_end != context_line_end
      else:
        newline_required = False
        trace = None


      color = symbols.color_bright_black if not (
        (isinstance(frame.env, ModuleEnvironment) and (frame.env.kind == 'user')) or
        (frame_index == 0)
      ) else ''

      file.write(frame_prefix)
      file.write(color)

      if frame.target is not None:
        target_name = None

        for node in [frame.target.node, *frame.target.parents[::-1]]:
          match node:
            case ast.AsyncFunctionDef(name=name) | ast.FunctionDef(name=name):
              file.write('at function')
              target_name = name
              break
            case ast.ClassDef(name=name):
              file.write('at class')
              target_name = name
              break
            case ast.Module():
              file.write(f'at module')
              break

        if target_name is not None:
          file.write(f' {symbols.color_underline}{target_name}{symbols.color_reset}{color}')

      match frame.env:
        case LabeledEnvironment(label):
          file.write(f'at fragment {label}')
        case ModuleEnvironment():
          if frame.env.name is not None:
            file.write(f' in {frame.env.name}')

          if frame.env.relative_path is not None:
            file.write(' (')

            if frame.env.kind == 'user':
              file.write('./')

            file.write(f'{frame.env.relative_path}')

            if (frame.env.kind != 'internal') and (line_start is not None):
              file.write(f':{line_start}')

            file.write(')')

      if frame.reraise:
        file.write(' [re-raise]')

      if (atom.repeat > 1) and (len(atom.keys) == 1):
        file.write(f' [repeated {atom.repeat} times]')

      # Trace ends with a newline
      file.write(f'{symbols.color_reset}\n{trace or ''}')

    if repeat_box_prefix is not None:
      file.write(f'{repeat_box_prefix}{symbols.box_up_right}{symbols.box_horizontal * 3}\n')
      newline_required = True

  if (not is_last) and newline_required:
    file.write(f'{prefix}\n')
