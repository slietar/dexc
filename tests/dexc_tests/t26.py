def main():
  def long_long_long_long_long_long_long_long_long_long_long_function():
    e = Exception('This is a long long long long long long long long long long long long long long long long long exception')

    x = 'This is a long long long long long long long long long long long long long long long long long note.'

    e.add_note('This is a normal note.')
    e.add_note(x)
    e.add_note(f'{x}\n{x}')

    raise e

  long_long_long_long_long_long_long_long_long_long_long_function()
