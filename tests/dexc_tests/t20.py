import sys


def main():
  old_recursion_limit = sys.getrecursionlimit()
  sys.setrecursionlimit(50)

  try:
    import scipy
  finally:
    sys.setrecursionlimit(old_recursion_limit)
