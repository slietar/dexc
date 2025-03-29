import sys
from pathlib import Path
from types import TracebackType
from typing import Iterable, Optional, Reversible, Sequence


class UnreachableError(Exception):
  pass


def create_tb(start_depth: int = 0):
  tb: Optional[TracebackType] = None
  depth = start_depth + 2

  while True:
    try:
      frame = sys._getframe(depth)
      depth += 1
    except ValueError:
      break

    tb = TracebackType(tb, frame, frame.f_lasti, frame.f_lineno)

  return tb


def find_common_ancestors[T](items: Iterable[Iterable[T]], /) -> Sequence[T]:
  items_iter = iter(items)

  try:
    current_ancestors = list(next(items_iter))
  except StopIteration:
    raise ValueError('At least one item is required')

  for item in items_iter:
    ancestor_index = 0

    for current_ancestor, item_ancestor in zip(current_ancestors, item):
      if current_ancestor != item_ancestor:
        break

      ancestor_index += 1

    current_ancestors = current_ancestors[:ancestor_index]

  return current_ancestors


def get_relative_path(path: Path, /) -> tuple[Optional[Path], bool]:
  cwd = Path.cwd()
  roots = [p for path in sys.path if path and (p := Path(path)) != cwd]

  for root in roots:
    try:
      relative_path = path.relative_to(root)
    except ValueError:
      pass
    else:
      return relative_path, True

  try:
    relative_path = path.relative_to(cwd)
  except ValueError:
    pass
  else:
    return relative_path, False

  return None, False


def reversed_if[T](it: Reversible[T], condition: bool, /) -> Iterable[T]:
  if condition:
    return reversed(it)
  else:
    return it


def lcount_whitespace(text: str, chars: Optional[str] = None, /):
  return len(text) - len(text.lstrip(chars))

def rcount_whitespace(text: str, chars: Optional[str] = None, /):
  return len(text) - len(text.rstrip(chars))

def wrap_line(line: str, /, *, maintain_indent: bool = True, max_indent: int = 20, width: int): # -> Iterable[str]:
  line_indent = min(len(line) - len(line.lstrip()), max_indent) if maintain_indent else 0
  available_width = width - line_indent

  current_index = line_indent

  while len(line) - current_index > available_width:
    split_index = line.rfind(' ', current_index, current_index + available_width + 1)

    if split_index >= 0:
      left_index = split_index - rcount_whitespace(line[current_index:split_index])
      right_index = split_index + 1
    else:
      left_index = current_index + available_width
      right_index = current_index + available_width

    yield line[:line_indent] + line[current_index:left_index]
    current_index = right_index + lcount_whitespace(line[right_index:])

  yield line[:line_indent] + line[current_index:]


# if __name__ == '__main__':
#   split = list(wrap_line('  Lorem ipsum dolor sit amet, consectetur adipisci elit.', maintain_indent=True, width=12))

#   print(split)

#   for line in split:
#     print(line)
