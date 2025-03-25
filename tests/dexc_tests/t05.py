def main():
  def produce_exc(name: str):
    try:
      raise Exception(name)




    except Exception as e:
      return e

  def a(x: int):
    if x == 0:
      raise Exception('Done')

    b(x)

  def b(x: int):
    return a(x - 1)

  def c(x: int):
    try:
      b(7)
    except Exception as e:
      return e

  def d():
    raise ExceptionGroup('Group3', [
      produce_exc('F'),
      produce_exc('G'),
    ])

  def e():
    try:
      d()
    except Exception as e:
      return e


  raise ExceptionGroup('Group', [
    produce_exc('A'),
    produce_exc('B'),
    Exception('C'),
    c(4),
    ExceptionGroup('Group2', [
      produce_exc('D'),
      produce_exc('E')
    ]),
    Exception('D'),
    e(),
  ])
