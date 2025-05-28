from jax import jit


def main():
  @jit
  def f(x, neg):
    return -x if neg else x

  f(1, True)
