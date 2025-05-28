def main():
  def produce_exc(name: str):
    try:
      raise Exception(name)




    except Exception as e:
      e.add_note('note 1')
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
    e = ExceptionGroup('Group3\nhere', [
      produce_exc('F'),
      produce_exc('G'),
    ])

    e.add_note('note 2')
    raise e

  def e():
    try:
      d()
    except Exception as e:
      return e


  g = ExceptionGroup('Group', [
    produce_exc('A'),
    produce_exc('B'),
    Exception('C'),
    c(4),
    ExceptionGroup('Group2\nhere', [
      produce_exc('D\nd'),
      produce_exc('E')
    ]),
    Exception('D'),
    e(),
  ])

  g.add_note('note 3')

  raise g
