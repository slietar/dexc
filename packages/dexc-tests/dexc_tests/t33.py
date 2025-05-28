from pathlib import Path
import sys

old_path = sys.path
sys.path.append(str(Path(__file__).parent / 't33_a'))
from t33.foo_long_long_long_long_long.bar.baz.foo_long_long_long_long_long.bar.baz import call
sys.path = old_path


def main():
  def a():
    raise Exception

  call(a)
