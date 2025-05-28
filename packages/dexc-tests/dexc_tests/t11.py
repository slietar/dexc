def main():
  def a(x: int):
    b(x)

  def b(x: int):
    if x == 0:
      raise Exception('Done')

    a(x - 1)

  a(8)
