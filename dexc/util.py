from pathlib import Path


def format_path(path: Path, relative_to: Path = Path.cwd()):
  try:
    return path.relative_to(relative_to)
  except ValueError:
    return path.name

def try_read_text(path: Path):
  try:
    return path.read_text()
  except OSError:
    return None
