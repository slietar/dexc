import sys


# See: https://stackoverflow.com/questions/15411967/how-can-i-check-if-code-is-executed-in-the-ipython-notebook
def get_ipython():
  if not 'IPython' in sys.modules:
    return None

  from IPython.core.getipython import get_ipython
  return get_ipython()
