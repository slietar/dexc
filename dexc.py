"""
Exception formatter that produces readable stack traces.
"""

__version__ = '0.1.0'


import ast
from dataclasses import dataclass
import itertools
import math
import os
import sys
from pathlib import Path
from types import TracebackType
from typing import IO, Literal, Optional


# TODO: Better checks
# TODO: Improve support for exception groups
# TODO: Avoid repeating recursive calls e.g. infinite loop
# TODO: Maximum screen width
# TODO: Option to reverse order
# TODO: Better highlight re-raises
# TODO: Handle multiprocessing.pool.RemoteTraceback which currently is text
# TODO: Better highlighting using ast data (e.g. only highlight first line of for loop)


@dataclass(slots=True)
class EscapeSequences:
  bright_black: str
  italic: str
  red: str
  reset: str
  underline: str

  def __init__(self, file: IO, *, disable_color: bool = False):
    if not (disable_color or not file.isatty() or os.environ.get('NO_COLOR')):
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


def get_integer_width(x: int, /):
  return max(math.ceil(math.log10(x + 1)), 1)

def get_line_indentation(line: str, /):
  return len(line) - len(line.lstrip())

def get_common_indentation(lines: list[str], /):
  return min(len(line) - len(stripped_line) for line in lines if (stripped_line := line.lstrip()))


def identify_node(mod: ast.Module, line_start: int, line_end: int, col_start: int, col_end: int) -> ast.Module | ast.expr | ast.stmt:
  best_candidate: ast.Module | ast.expr | ast.stmt = mod

  def node_matches(node: ast.expr | ast.stmt):
    assert node.end_lineno is not None

    # TODO: Improve to support columns
    return (node.lineno <= line_start) and (node.end_lineno >= line_end)

  while True:
    new_candidates = list[ast.expr | ast.stmt]()

    match best_candidate:
      case ast.ClassDef(body=body):
        new_candidates += body
      case ast.ExceptHandler(type, name, body):
        new_candidates += [type, *body]
      case ast.Expr(value):
        new_candidates.append(value)
      case ast.AsyncFunctionDef(body=body) | ast.FunctionDef(body=body):
        new_candidates += body
      case ast.If(test, body, orelse):
        new_candidates += [test, *body, *orelse]
      case ast.Module(body=body):
        new_candidates += body
      case ast.For(target, iter, body, orelse, type_comment):
        new_candidates += [target, iter, *body, *orelse]
      case ast.Try(body, handlers, orelse, finalbody) | ast.TryStar(body, handlers, orelse, finalbody):
        new_candidates += [*body, *handlers, *orelse, *finalbody]
      case _:
        return best_candidate

    candidates_matching = [candidate for candidate in new_candidates if node_matches(candidate)]

    if len(candidates_matching) == 1:
      best_candidate = candidates_matching[0]
    else:
      return best_candidate # type: ignore


@dataclass(kw_only=True, slots=True)
class Options:
  max_context_lines_after: int = 2
  max_context_lines_before: int = 3
  max_target_lines: int = 5
  skip_indentation_highlight: bool = True
  remove_common_indentation: bool = True


def format_frame(
    escape: EscapeSequences,
    frame_index: int,
    func_name: str,
    raw_path: str,
    positions: Optional[tuple[Optional[int], Optional[int], Optional[int], Optional[int]]],
    prefix: str,
    options: Options
  ):
  is_reraise = False
  trace = None

  if raw_path[0] == '<':
    kind = 'internal'
    module_name = raw_path
  else:
    # Locate module

    frame_path = Path(raw_path)

    for sys_path in sys.path:
      try:
        rel_path = frame_path.relative_to(sys_path)
      except ValueError:
        pass
      else:
        *directories, file_name = rel_path.parts

        module_path = directories + [file_name.removesuffix('.py')]
        module_name = '.'.join(module_path)

        if module_path[0] in sys.stdlib_module_names:
          kind = 'std'
        else:
          try:
            frame_path.relative_to(Path.cwd())
          except ValueError:
            kind = 'lib'
          else:
            kind = 'user'

        break
    else:
      kind = 'user'
      module_name = raw_path


    if (frame_index == 0) or (
      (kind == 'user') and
      (frame_index < 3)
    ):
      # Produce trace

      if positions is not None:
        try:
          frame_contents = frame_path.read_text()
        except OSError:
          frame_contents = None

        if frame_contents is not None:
          # Obtain target line range

          line_start, line_end, col_start, col_end = positions
          code_lines = frame_contents.splitlines()

          # Line numbers start at 1
          assert (line_start is not None) and (line_end is not None) and (col_start is not None) and (col_end is not None)


          # Detect re-raise

          if frame_index > 0:
            mod = ast.parse(frame_contents)
            node = identify_node(mod, line_start, line_end, col_start, col_end)
            is_reraise = isinstance(node, ast.Raise)


          # Compute target line range

          # Ensure there are no more than max_total_lines target lines
          if line_end - line_start + 1 > options.max_target_lines:
            # The "more lines" message always mentions at least 2 lines
            line_end_cut = line_start + options.max_target_lines - 2
          else:
            line_end_cut = line_end

          # Old version
          # line_end_cut = line_start + min(line_end - line_start, max_target_lines - 1)


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

          indent = ' ' * 4
          trace = f''

          for rel_line_index, line in enumerate(code_lines[(context_line_start - 1):(line_start - 1)]):
            line_number = context_line_start + rel_line_index
            trace += f'{prefix}{escape.bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{escape.reset}\n'


          # Display target

          target_lines = code_lines[(line_start - 1):line_end_cut]

          for rel_line_index, line in enumerate(target_lines):
            line_number = line_start + rel_line_index
            line_indent = (get_line_indentation(line) if options.skip_indentation_highlight else 0)

            if line_number == line_start:
              anchor_start = col_start

              if line_start == line_end:
                anchor_end = col_end
              else:
                anchor_end = len(line) - col_start
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

  color = escape.bright_black if (kind != 'user') and (frame_index != 0) else ''

  return f'{prefix}{color}  at {escape.underline if trace is not None else ''}{func_name}{escape.reset}'\
    + f'{color} ({module_name}{f':{positions[0]}' if (kind != 'internal') and (positions is not None) and (positions[0] is not None) else ''})'\
    + f'{' [re-raise]' if is_reraise else ''}{escape.reset}\n' + (trace or '')


def write_exc(start_exc: BaseException, file: IO[str], *, escape: EscapeSequences, options: Options, prefix: str):
  screen_width = 80

  if isinstance(start_exc, (BaseExceptionGroup, ExceptionGroup)):
    write_exc_core(start_exc, file, escape=escape, options=options, prefix=f' | {prefix}', prefix_first=f'{prefix} + ')

    line = f'{prefix} +--+'
    file.write(f'{line}{'-' * (screen_width - len(line))}\n')

    for exc in start_exc.exceptions:
      write_exc(exc, file, escape=escape, options=options, prefix=f'    | {prefix}')

      line = f'{prefix}    +'
      file.write(f'{line}{'-' * (screen_width - len(line))}\n')
  else:
    write_exc_core(start_exc, file, escape=escape, options=options, prefix=prefix, prefix_first=prefix)


def write_exc_core(start_exc: BaseException, file: IO[str], *, escape: EscapeSequences, options: Options, prefix: str, prefix_first: str):
  # List exceptions

  current_exc = start_exc
  excs = list[tuple[BaseException, Literal['base', 'cause', 'context']]]()
  excs.append((current_exc, 'base'))

  while True:
    if current_exc.__cause__:
      current_exc = current_exc.__cause__
      excs.append((current_exc, 'cause'))
    elif current_exc.__context__:
      current_exc = current_exc.__context__
      excs.append((current_exc, 'context'))
    else:
      break


  # Print exceptions

  for exc, exc_kind in excs:
    # Write possible cause or context explanation

    match exc_kind:
      case 'base':
        pass
      case 'cause':
        file.write(f'{prefix}\n{escape.italic}[Caused by]{escape.reset}\n{prefix}\n')
      case 'context':
        file.write(f'{prefix}\n{escape.italic}[Raised while handling]{escape.reset}\n{prefix}\n')


    # Write exception message

    file.write(f'{prefix_first}{type(exc).__name__}: {exc}\n')


    # List frames

    current_tb = exc.__traceback__
    tbs = list[TracebackType]()

    while current_tb:
      tbs.append(current_tb)
      current_tb = current_tb.tb_next


    # Write frames

    is_syntax_error = isinstance(exc, SyntaxError)

    if is_syntax_error:
      file.write(format_frame(
        escape=escape,
        frame_index=0,
        func_name=Path(exc.filename).name,
        prefix=prefix,
        raw_path=exc.filename,
        positions=(
          exc.lineno,
          exc.end_lineno,
          (exc.offset - 1) if exc.offset is not None else None,
          (
            (exc.end_offset - 1) if exc.end_offset > 0 else exc.offset
          ) if exc.end_offset is not None else None
        ),
        options=options
      ))

    for tb_index, tb in enumerate(reversed(tbs)):
      frame = tb.tb_frame
      frame_code = frame.f_code
      raw_path = frame_code.co_filename

      positions = next(
        itertools.islice(frame_code.co_positions(), tb.tb_lasti // 2, None)
      ) if tb.tb_lasti >= 0 else None

      file.write(format_frame(
        escape=escape,
        frame_index=(tb_index + (1 if is_syntax_error else 0)),
        func_name=frame_code.co_qualname,
        prefix=prefix,
        raw_path=raw_path,
        positions=positions,
        options=options
      ))


def dump(
    start_exc: BaseException,
    /,
    file: IO[str],
    *,
    disable_color: bool = False,
    options: Options = Options()
  ):
  escape = EscapeSequences(file, disable_color=disable_color)

  write_exc(start_exc, file, escape=escape, options=options, prefix='')


def install(file: IO[str] = sys.stderr):
  def except_hook(start_exc_type: type[BaseException], start_exc: BaseException, start_tb: TracebackType):
    dump(start_exc, file)

  def unraisable_hook(arg):
    dump(arg.exc_value, file)

  sys.excepthook = except_hook
  sys.unraisablehook = unraisable_hook


__all__ = [
  'dump',
  'install',
]
