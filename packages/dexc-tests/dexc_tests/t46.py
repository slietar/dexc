import warnings


def main():
  warnings.warn("This is a test warning", UserWarning)
  warnings.warn(UserWarning("This is another test warning"))

  f = open(__file__)
  f = None
