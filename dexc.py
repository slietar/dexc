import itertools
import math
import sys
from pathlib import Path
from types import TracebackType
from typing import IO, Literal


# TODO: Better checks
# TODO: Support for exception groups
# TODO: Fix ANSI escape sequences
# TODO: Remove common indentation
# TODO: Disabling color
# TODO: User vs lib tb kinds
# TODO: Max number of displayed lines for a tb
# TODO: Support for format() instead of directly writing
# TODO: Avoid repeating recursive calls e.g. infinite loop


class EscapeSeq:
  bright_black = '\033[90m'
  italic = '\033[3m'
  red = '\033[31m'
  reset = '\033[0m'
  underline = '\033[4m'

MAX_CONTEXT_LINES_BEFORE = 3
MAX_CONTEXT_LINES_AFTER = 2

def get_integer_width(x: int):
  return max(math.ceil(math.log10(x + 1)), 1)


def dump(start_exc: BaseException, /, file: IO[str]):
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

  for exc, exc_kind in excs:
    match exc_kind:
      case 'base':
        pass
      case 'cause':
        file.write(f'\n{EscapeSeq.italic}[Caused by]{EscapeSeq.reset}\n\n')
      case 'context':
        file.write(f'\n{EscapeSeq.italic}[Raised while handling]{EscapeSeq.reset}\n\n')

    file.write(f'{type(exc).__name__}: {exc}\n')

    current_tb = exc.__traceback__
    tbs = list[TracebackType]()

    while current_tb:
      tbs.append(current_tb)
      current_tb = current_tb.tb_next

    for tb_index, tb in enumerate(reversed(tbs)):
      frame = tb.tb_frame
      frame_code = frame.f_code
      frame_path_str = frame_code.co_filename

      if frame_path_str[0] == '<':
        kind = 'internal'
        module_name = frame_path_str
        trace = None
      else:
        # Locate module

        frame_path = Path(frame_path_str)

        # for sys_path in (*sys.path, Path.cwd()):
        for sys_path in sys.path:
          try:
            rel_path = frame_path.relative_to(sys_path)
          except ValueError:
            pass
          else:
            *directories, file_name = rel_path.parts

            module_path = directories + [file_name.removesuffix('.py')]
            module_name = '.'.join(module_path)
            kind = 'std' if module_path[0] in sys.stdlib_module_names else 'user'

            break
        else:
          kind = 'user'
          module_name = frame_path_str


        if (tb_index == 0) or (
          (kind == 'user') and
          (tb_index < 3)
        ):
          # Get positions

          if tb.tb_lasti < 0:
            positions = None
          else:
            positions_gen = frame_code.co_positions()
            positions = next(itertools.islice(positions_gen, tb.tb_lasti // 2, None))


          # Produce trace

          if positions is not None:
            line_start, line_end, col_start, col_end = positions
            code_lines = frame_path.read_text().splitlines()

            # Line numbers start at 1
            assert (line_start is not None) and (line_end is not None) and (col_start is not None) and (col_end is not None)

            indent = ' ' * 4
            trace = ''


            # Compute context line range

            context_line_start = max(line_start - MAX_CONTEXT_LINES_BEFORE, 1)
            context_line_end = min(line_end + MAX_CONTEXT_LINES_AFTER, len(code_lines))

            while (context_line_start < line_start) and (not (context_line := code_lines[context_line_start - 1]) or context_line.isspace()):
              context_line_start += 1

            # This must be done beforehand in order to calculate the maximum line width
            while (context_line_end > line_end) and (not (context_line := code_lines[context_line_end - 1]) or context_line.isspace()):
              context_line_end -= 1


            # Compute line number width

            line_number_width = get_integer_width(context_line_end)


            # Display context before target

            if context_line_start != line_start:
              trace += EscapeSeq.bright_black

            for rel_line_index, line in enumerate(code_lines[(context_line_start - 1):(line_start - 1)]):
              line_number = context_line_start + rel_line_index
              trace += f'{indent}{line_number: >{line_number_width}} {line}\n'

            if context_line_start != line_start:
              trace += EscapeSeq.reset


            # Display target

            target_lines = code_lines[(line_start - 1):line_end]

            for rel_line_index, line in enumerate(target_lines):
              line_number = line_start + rel_line_index
              line_indent = len(line) - len(line.lstrip())

              if rel_line_index == 0:
                anchor_offset = col_start

                if line_start == line_end:
                  anchor_length = col_end - col_start
                else:
                  anchor_length = len(line) - col_start
              elif rel_line_index == (len(target_lines) - 1):
                anchor_offset = line_indent
                anchor_length = col_end - line_indent
              else:
                anchor_offset = line_indent
                anchor_length = len(line) - line_indent

              trace += f'{indent}{line_number: >{line_number_width}} {line}\n'
              trace += indent + ' ' * (line_number_width + 1 + anchor_offset) + EscapeSeq.red + '^' * anchor_length + EscapeSeq.reset + '\n'

            # Display context after target

            if context_line_end != line_end:
              trace += EscapeSeq.bright_black

            for rel_line_index, line in enumerate(code_lines[line_end:context_line_end]):
              line_number = line_end + rel_line_index + 1
              trace += f'{indent}{line_number: >{line_number_width}} {line}\n'

            if context_line_end != line_end:
              trace += EscapeSeq.reset

            trace += '\n'
          else:
            trace = None
        else:
          trace = None

      color = EscapeSeq.bright_black if (kind != 'user') and (tb_index != 0) else ''
      file.write(f'{color}  at {EscapeSeq.underline if trace is not None else ''}{frame_code.co_qualname}{EscapeSeq.reset}{color} ({module_name}{f':{frame.f_lineno}' if kind != 'internal' else ''}){EscapeSeq.reset}\n')

      if trace is not None:
        file.write(trace)


def install(file: IO[str] = sys.stderr):
  def hook(start_exc_type: type[BaseException], start_exc: BaseException, start_tb: TracebackType):
    dump(start_exc, file)

  sys.excepthook = hook


__all__ = [
  'dump',
  'install',
]
