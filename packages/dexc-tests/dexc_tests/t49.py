# Requires Python >= 3.14

import concurrent.interpreters
import sys


def main():
  if sys.version_info >= (3, 14):
    interpreter = concurrent.interpreters.create()

    def a():
      import dexc  # noqa: F401
      raise Exception("This is an exception from the interpreter")

    try:
      interpreter.exec(a)
    finally:
      interpreter.close()
