import sys
from pathlib import Path


def format_path(path: Path, /):
  cwd = Path.cwd()
  roots = [
    *(Path(path) for path in sys.path if path),
    cwd,
  ]

  for root in roots:
    try:
      relative_path = path.relative_to(root)
    except ValueError:
      pass
    else:
      if root == cwd:
        return f'./{relative_path}'
      else:
        return relative_path

  return path.name

def try_read_text(path: Path, /):
  try:
    return path.read_text()
  except OSError:
    return None
