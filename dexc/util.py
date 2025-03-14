import sys
from pathlib import Path
from typing import Optional


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

def try_read_text(path: Path, /):
  try:
    return path.read_text()
  except OSError:
    return None
