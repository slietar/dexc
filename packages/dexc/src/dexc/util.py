import math
import re
import sys
from pathlib import Path
from types import TracebackType
from typing import Callable, Iterable, Optional, Reversible, Sequence, TypeVar


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
  total_len = sum(part_lens[:left_index]) + max(left_index - 1, 0) * separator_width

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
  total_len += sum(part_lens[right_index:]) + max(len(parts) - right_index - 1, 0) * separator_width

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


T = TypeVar('T')

def find_common_ancestors(items: Iterable[Iterable[T]], /) -> Sequence[T]:
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


def reversed_if(it: Reversible[T], condition: bool, /) -> Iterable[T]:
  if condition:
    return reversed(it)
  else:
    return it


def lcount_lines_until_nonempty(lines: Sequence[str], /, *, start: int = 0):
  return start + next((index for index, line in enumerate(lines[start:]) if line), len(lines) - start)

def lcount_whitespace(text: str, chars: Optional[str] = None, /):
  return len(text) - len(text.lstrip(chars))

def rcount_whitespace(text: str, chars: Optional[str] = None, /):
  return len(text) - len(text.rstrip(chars))


def get_common_indentation(lines: list[str], /):
  return min(
    line_indent for line in lines if (line_indent := lcount_whitespace(line)) < len(line)
  )

def get_integer_width(x: int, /):
  return max(math.ceil(math.log10(x + 1)), 1)



def wrap_into_paragraph(
  text: str, /, *,
  link: Optional[Callable] = None,
  maintain_indent: bool = True,
  max_indent: int = 20,
  max_trailing_whitespace: int = 20,
  width: int,
):
  indent = min(lcount_whitespace(text), max_indent) if maintain_indent else 0
  truncated_text = text[indent:]

  line_indices = wrap_into_paragraph_indices(
    truncated_text,
    max_trailing_whitespace=max_trailing_whitespace,
    width=(width - indent),
  )

  if link is not None:
    for line, line_len in wrap_into_paragraph_format_links(truncated_text, line_indices, link=link):
      yield (
        text[:indent] + line,
        indent + line_len,
      )
  else:
    for line_start, line_end in line_indices:
      yield (
        text[:indent] + truncated_text[line_start:line_end],
        indent + line_end - line_start,
      )


BREAK_PATTERNS = [
  re.compile(str_pattern, re.IGNORECASE) for str_pattern in [
    r'\s+()',
    # Same as .\b() but with considering underscores as non-word characters
    r'.(?:(?<=[a-z])(?=[^a-z])|(?<=[^a-z])(?=[a-z]))()',
    r'.()',
  ]
]

def wrap_into_paragraph_indices(text: str, /, *, max_trailing_whitespace: int = 20, width: int): # -> Iterable[str]:
  current_index = 0
  stripped_text = text.rstrip()

  while len(stripped_text) - current_index > width:
    for pattern in BREAK_PATTERNS:
      match = pattern.search(stripped_text[current_index:(current_index + width + 1)][::-1])

      if match:
        assert match.start(1) > 0
        offset = match.start(1) - 1

        if 0 <= offset < min(max_trailing_whitespace + 1, width):
          left_index = current_index + width - offset
          right_index = left_index + lcount_whitespace(stripped_text[left_index:])
          break
    else:
      # The last pattern should always match
      raise UnreachableError

    yield current_index, left_index
    current_index = right_index + lcount_whitespace(stripped_text[right_index:])

  yield current_index, len(stripped_text)


URL_PATTERN = re.compile(r'https?:\/\/[^\s]+')

def wrap_into_paragraph_format_links(text: str, line_indices: Iterable[tuple[int, int]], /, *, link: Callable) -> Iterable[tuple[str, int]]:
  matches = [(match.start(), match.end(), match.group()) for match in URL_PATTERN.finditer(text)]

  current_match_index = 0
  current_match_started = False

  for line_start, line_end in line_indices:
    current_index = line_start

    formatted_line = ''
    formatted_line_len = 0

    while True:
      if current_match_index >= len(matches):
        formatted_line += text[current_index:line_end]
        formatted_line_len += line_end - current_index
        break

      current_match_start, current_match_end, current_match_url = matches[current_match_index]

      if current_match_started:
        new_current_index = min(current_match_end, line_end)

        formatted_line += link(text[current_index:new_current_index], current_match_url)
        formatted_line_len += new_current_index - current_index

        current_index = new_current_index

        # If we didn't reach the match end
        if current_index < current_match_end:
          break

        current_match_started = False
        current_match_index += 1
      else:
        new_current_index = min(current_match_start, line_end)

        formatted_line += text[current_index:new_current_index]
        formatted_line_len += new_current_index - current_index

        current_index = new_current_index

        # If we didn't reach the match start
        if current_index < current_match_start:
          break

        current_match_started = True

    yield formatted_line, formatted_line_len


def wrap_into_ellipsis(target: str, /, *, ellipsis: str, margin: int = 0, width: int):
  assert len(ellipsis) <= width

  if len(target) <= width - margin:
    return target

  return target[:(width - len(ellipsis))].rstrip() + ellipsis
