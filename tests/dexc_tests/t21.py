def main():
  def f(x):
    raise Exception

  import scipy
  scipy.optimize.fmin(f, [0])
