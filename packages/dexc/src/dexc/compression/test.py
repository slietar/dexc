import functools
from .greedy import compress as compress_greedy
from .optimal import compress as compress_optimal


if __name__ == '__main__':
  # seq = [random.randint(0, 9) for _ in range(10000)]
  # seq = list('22222210010122113333030111123333303200112330322320')
  seq = list('12123123123') # Greedy result is worse than optimal
  # seq = list('2345111116789')
  # seq = list('1' * 10)

  for func, name in [
    (compress_greedy, 'Greedy forwards'),
    (functools.partial(compress_greedy, backwards=True), 'Greedy backwards'),
    (compress_optimal, 'Optimal'),
  ]:
    print(f'Method: {name}')

    atoms = func(seq)

    for atom in atoms:
      print(''.join(map(str, atom.keys)) * atom.repeat_count, end='')

    print()

    for atom in atoms:
      print(''.join(map(str, atom.keys)), end='')
      print('-' * len(atom.keys) * (atom.repeat_count - 1), end='')
      # print(''.join(map(str, subseq)) * count, end='')

    print('\n')
