import sys
from pathlib import Path
from typing import Iterable, Optional, Reversible, Sequence


class UnreachableError(Exception):
  pass

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


def try_read_text(path: Path, /):
  try:
    return path.read_text()
  except OSError:
    return None
