def main():
  def produce_exc(name: str):
    try:
      raise Exception(name)
    except Exception as e:
      return e

  raise ExceptionGroup('Group', [
    produce_exc('A'),
    produce_exc('B'),
    Exception('C'),
    ExceptionGroup('Group2', [
      produce_exc('D'),
      produce_exc('E')
    ]),
    Exception('D'),
  ])
