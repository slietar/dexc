import re
import sys
from pathlib import Path
from types import TracebackType
from typing import Iterable, Optional, Reversible, Sequence


class UnreachableError(Exception):
  pass


def condense_parts(parts: Sequence[str], /, *, ellipsis: str, priority_left: bool = False, separator: str, width: int):
  part_lens = [len(part) for part in parts]
  left_index, right_index = condense_seq(
    part_lens,
    ellipsis_width=len(ellipsis),
    priority_left=priority_left,
    separator_width=len(separator),
    width=width,
  )

  return format_condensed_seq(
    parts,
    part_lens,
    (left_index, right_index),
    ellipsis=ellipsis,
    ellipsis_width=len(ellipsis),
    separator=separator,
    separator_width=len(separator),
  )


def condense_seq(
  part_lens: Sequence[int],
  /, *,
  ellipsis_width: int,
  priority_left: bool = False,
  separator_width: int,
  width: int,
):
  assert width >= ellipsis_width

  left_index = 0
  right_index = len(part_lens)

  left_width = 0
  right_width = 0

  while left_index != right_index:
    left_sep_width = separator_width if left_index > 0 else 0
    right_sep_width = separator_width if right_index < len(part_lens) else 0

    new_left_width = left_width + left_sep_width + part_lens[left_index]
    new_right_width = right_width + right_sep_width + part_lens[right_index - 1]

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

  return left_index, right_index


def format_condensed_seq(
  parts: Sequence[str],
  part_lens: Sequence[int],
  indices: tuple[int, int],
  *,
  ellipsis: str,
  ellipsis_width: int,
  separator: str,
  separator_width: int,
):
  left_index, right_index = indices
  output = separator.join(parts[:left_index])
  total_len = sum(part_lens[:left_index]) + left_index * separator_width

  if (left_index > 0) and (
    (right_index < len(parts)) or
    (left_index != right_index)
  ):
    output += separator
    total_len += separator_width

  if left_index != right_index:
    output += ellipsis
    total_len += ellipsis_width

    if right_index < len(parts):
      output += separator
      total_len += separator_width

  output += separator.join(parts[right_index:])
  total_len += sum(part_lens[right_index:]) + (len(parts) - right_index - 1) * separator_width

  return output, total_len


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

def wrap_into_paragraph(line: str, /, *, maintain_indent: bool = True, max_indent: int = 20, max_trailing_whitespace: int = 20, width: int): # -> Iterable[str]:
  line_indent = min(lcount_whitespace(line), max_indent) if maintain_indent else 0
  available_width = width - line_indent

  current_index = line_indent

  break_patterns = [
    re.compile(str_pattern) for str_pattern in [
      r'\s+()',
      r'.\b()',
      r'.()',
    ]
  ]

  while len(line) - current_index > available_width:
    for pattern in break_patterns:
      match = pattern.search(line[current_index:(current_index + available_width + 1)][::-1])

      if match:
        assert match.start(1) > 0
        offset = match.start(1) - 1

        if 0 <= offset < min(max_trailing_whitespace + 1, available_width):
          left_index = current_index + available_width - offset
          right_index = left_index + lcount_whitespace(line[left_index:])
          break
    else:
      # The last pattern should always match
      raise UnreachableError

    yield line[:line_indent] + line[current_index:left_index]
    current_index = right_index + lcount_whitespace(line[right_index:])

  yield line[:line_indent] + line[current_index:]


def wrap_into_ellipsis(target: str, /, *, ellipsis: str, margin: int = 0, width: int):
  assert len(ellipsis) <= width

  if len(target) <= width - margin:
    return target

  return target[:(width - len(ellipsis))] + ellipsis
