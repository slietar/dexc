def main():
  def a(x: int):
    if x == 0:
      raise Exception('Done')

    b(x)

  def b(x: int):
    a(x - 1)

  a(8)
