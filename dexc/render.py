import ast
import math
import os
import sys
from dataclasses import dataclass
from pprint import pprint
from typing import IO, Optional

from .util import format_path

from .extract import ExceptionChain, ExceptionItem, extract


# See: https://stackoverflow.com/questions/15411967/how-can-i-check-if-code-is-executed-in-the-ipython-notebook
def get_ipython():
  if not 'IPython' in sys.modules:
    return None

  from IPython.core.getipython import get_ipython
  return get_ipython()


def get_integer_width(x: int, /):
  return max(math.ceil(math.log10(x + 1)), 1)

def get_line_indentation(line: str, /):
  return len(line) - len(line.lstrip())

def get_common_indentation(lines: list[str], /):
  return min(len(line) - len(stripped_line) for line in lines if (stripped_line := line.lstrip()))


@dataclass(slots=True)
class EscapeSequences:
  bright_black: str
  italic: str
  red: str
  reset: str
  underline: str

  def __init__(self, file: IO, *, disable_color: bool = False):
    if (not disable_color) and (not os.environ.get('NO_COLOR')) and (file.isatty() or (get_ipython() is not None)):
      self.bright_black = '\033[90m'
      self.italic = '\033[3m'
      self.red = '\033[31m'
      self.reset = '\033[0m'
      self.underline = '\033[4m'
    else:
      self.bright_black = ''
      self.italic = ''
      self.red = ''
      self.reset = ''
      self.underline = ''


@dataclass(kw_only=True, slots=True)
class Options:
  ascii_only: bool = False
  chain_origin_on_top: bool = False
  inner_frame_on_top: bool = True
  max_context_lines_after: int = 2
  max_context_lines_before: int = 3
  max_target_lines: int = 5
  skip_indentation_highlight: bool = True
  remove_common_indentation: bool = True


def render(chain: ExceptionChain, file: IO[str], options: Options, *, _prefix: str = ''):
  escape = EscapeSequences(file)

  tree_corner = '+-- ' if options.ascii_only else '└── '
  tree_branch = '+-- ' if options.ascii_only else '├── '
  tree_line = '| ' if options.ascii_only else '│ '

  for item, relation in zip(chain.items[::-1], [None, *chain.relations[::-1]]) if options.chain_origin_on_top else zip(chain.items, [None, *chain.relations]):
    if relation is not None:
      file.write(f'{_prefix}')

      match relation:
        case 'cause':
          file.write(f'{escape.italic}[{'Causing' if options.chain_origin_on_top else 'Caused by'}]{escape.reset}\n{_prefix}\n{_prefix}')
        case 'context':
          file.write(f'{escape.italic}[{'Raising while handling' if options.chain_origin_on_top else 'Raised while handling'}]{escape.reset}\n{_prefix}\n{_prefix}')

    file.write(f'{type(item.instance).__name__}: {item.instance}\n')
    render_item(item, file, escape, options, prefix=(_prefix + (tree_line if item.children else '')))

    for child_index, child in enumerate(item.children):
      is_child_last = child_index == len(item.children) - 1

      file.write(f'{_prefix}{tree_corner if is_child_last else tree_branch}')
      render(child, file, options, _prefix=f'{_prefix}{'  ' if is_child_last else tree_line}  ')


def render_item(item: ExceptionItem, file: IO[str], escape: EscapeSequences, options: Options, *, prefix: str):
  iterator = enumerate(item.frames)

  if not options.inner_frame_on_top:
    iterator = reversed(list(iterator))

  for frame_index, frame in iterator:
    line_start = frame.area.line_start
    line_end = frame.area.line_end
    col_start = frame.area.col_start
    col_end = frame.area.col_end

    if (
      (frame_index == 0) or (
        (frame.module.kind == 'user') and
        (frame_index < 3)
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
        trace += f'{prefix}{escape.bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{escape.reset}\n'


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

        trace += f'{prefix}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}\n'
        trace += prefix + indent + ' ' * (line_number_width + 1 + anchor_start_sub)
        trace += escape.red
        trace += '^' * (anchor_end_sub - anchor_start_sub)
        trace += escape.reset + '\n'

      if line_end_cut != line_end:
        trace += f'{prefix}{indent}{' ' * (line_number_width + 1)}[{line_end - line_end_cut} more lines]\n'


      # Display context after target

      for rel_line_index, line in enumerate(code_lines[line_end:context_line_end]):
        line_number = line_end + rel_line_index + 1
        trace += f'{prefix}{escape.bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{escape.reset}\n'

      trace += f'{prefix}\n'
    else:
      trace = None

    color = escape.bright_black if (frame.module.kind != 'user') and (frame_index != 0) else ''

    if frame.target is not None:
      # target_name = frame.target.name
      for node in [frame.target.node, *frame.target.parents]:
        match node:
          case ast.FunctionDef(name=name):
            target_name = f'{color}at function {escape.underline if trace is not None else ''}{name}{escape.reset} '
            break
          case ast.ClassDef(name=name):
            target_name = f'{color}at class {escape.underline if trace is not None else ''}{name}{escape.reset} '
            break
      else:
        target_name = ''
    else:
      target_name = ''


    frame_formatted = f'{prefix}{target_name}'\
      + f'{color}in {format_path(frame.module.path)}{f':{line_start}' if (frame.module.kind != 'internal') and line_start is not None else ''} as {frame.module.name}'\
      + f'{' [re-raise]' if frame.reraise else ''}{escape.reset}\n' + (trace or '')

    file.write(frame_formatted)


if __name__ == '__main__':
  def err(msg: str):
    class A:
      raise Exception(msg)

  def ge(msg: str):
    try:
      try:
        err(msg + ' pre')
      except Exception as e:
        raise Exception(msg + ' post') from e
    except Exception as e:
      return e

  try:
    # raise ExceptionGroup('foo', [
    #   ge('bar'),
    #   ExceptionGroup('baz', [
    #     ge('qux'),
    #     ge('quux'),
    #   ]),
    #   ge('bar'),
    # ])
    class A:
      raise Exception('foo')
  except Exception as e:
    chain = extract(e)

  # pprint(chain)
  render(chain, sys.stderr, Options())
