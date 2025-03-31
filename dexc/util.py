import sys
from pathlib import Path
from types import TracebackType
from typing import Iterable, Optional, Reversible, Sequence


class UnreachableError(Exception):
  pass


def condense_path(parts: Sequence[str], /, *, ellipsis: str, priority_left: bool = False, width: int):
  left_index, right_index = condense_seq(
    [len(part) for part in parts],
    ellipsis_width=len(ellipsis),
    priority_left=priority_left,
    separator_width=1,
    width=width,
  )

  return format_condensed_seq(
    parts,
    (left_index, right_index),
    ellipsis=ellipsis,
    separator='/',
  )


def condense_seq(
  item_widths: Sequence[int],
  /, *,
  ellipsis_width: int,
  priority_left: bool = False,
  separator_width: int = 1,
  width: int,
):
  assert width >= ellipsis_width

  left_index = 0
  right_index = len(item_widths)

  left_width = 0
  right_width = 0

  # instric_width = sum(item_widths) + sep_width * (len(item_widths) - 1)
  # print(f'{instric_width=}')

  # if instric_width <= width:
  #   return 0, 0

  while left_index != right_index:
    left_sep_width = separator_width if left_index > 0 else 0
    right_sep_width = separator_width if right_index < len(item_widths) else 0

    new_left_width = left_width + left_sep_width + item_widths[left_index]
    new_right_width = right_width + right_sep_width + item_widths[right_index - 1]

    joining = right_index - left_index == 1

    left_grow = new_left_width + (separator_width + ellipsis_width if not joining else 0) + right_sep_width + right_width <= width
    right_grow = left_width + left_sep_width + (ellipsis_width + separator_width if not joining else 0) + new_right_width <= width

    if left_grow and (
      ((left_width <= right_width) and priority_left) or
      (not right_grow)
    ):
      left_index += 1
      left_width = new_left_width
    elif right_grow:
      right_index -= 1
      right_width = new_right_width
    else:
      break

    # print('!', new_left_width + join_width + right_width, width)
    # print(new_left_width, join_width, right_width, width)
    # if (left_width < right_width) and ():
    #   left_index += 1
    #   left_width = new_left_width
    #   continue

    # if left_width + left_sep_width + (ellipsis_width + sep_width if not joining else 0) + new_right_width <= width:
    #   right_index -= 1
    #   right_width = new_right_width
    #   continue

    # if new_left_width + (sep_width + ellipsis_width if not joining else 0) + right_sep_width + right_width <= width:
    #   left_index += 1
    #   left_width = new_left_width
    #   continue

    # break

  return left_index, right_index


def format_condensed_seq(items: Sequence[str], indices: tuple[int, int], *, ellipsis: str, separator: str):
  left_index, right_index = indices
  output = separator.join(items[:left_index])

  if (left_index > 0) and (
    (right_index < len(items)) or
    (left_index != right_index)
  ):
    output += separator

  if left_index != right_index:
    output += ellipsis

    if right_index < len(items):
      output += separator

  output += separator.join(items[right_index:])

  return output


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


def wrap_with_ellipsis(target: str, /, *, ellipsis: str, width: int):
  assert len(ellipsis) <= width

  if len(target) <= width:
    return target

  return target[:(width - len(ellipsis))] + ellipsis
