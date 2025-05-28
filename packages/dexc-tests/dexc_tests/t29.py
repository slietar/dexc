def main():
  def a():
    __tracebackhide__ = True

    raise Exception

  a()
