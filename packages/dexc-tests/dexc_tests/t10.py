def main():
  e = Exception('test\nfoo')
  e.add_note('note 1')
  e.add_note('note 1')

  e.add_note('''Falsifying example: test(
  x=-1,
)''')
  e.add_note('note 1')

  raise e
