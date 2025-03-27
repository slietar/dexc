from typing import Callable, Sequence

from .compression import Atom, MeasuredSolution


def compress[T, S](
  items: Sequence[T],
  /,
  *,
  key: Callable[[T], S] = (lambda item: item),
  max_repeat_len: int = 10,
):
  keys = list(map(key, items))
  repeats = dict[int, tuple[int, int]]()

  index = 0

  while index < len(keys):
    for repeat_len in reversed(range(1, min(max_repeat_len, index) + 1)):
      if (keys[(index - repeat_len):index] == keys[index:(index + repeat_len)]) and not any(i in repeats for i in range(index - repeat_len, index)):
        repeat = 2

        while keys[(index + repeat_len * (repeat - 1)):(index + repeat_len * repeat)] == keys[index:(index + repeat_len)]:
          repeat += 1

        repeats[index - repeat_len] = repeat_len, repeat
        index += repeat_len * (repeat - 1)
        break
    else:
      index += 1

  atoms = list[Atom[T, S]]()
  index = 0

  while index < len(keys):
    if index in repeats:
      repeat_len, repeat = repeats[index]
    else:
      repeat_len = 1
      repeat = 1

    atoms.append(Atom(
      keys=tuple(keys[index:(index + repeat_len)]),
      realization=items[index:(index + repeat_len * repeat)],
      repeat=repeat,
    ))

    index += repeat_len * repeat

  return MeasuredSolution(atoms, cost=0.0)


if __name__ == '__main__':
  seq = list('12312231233')

  solved = compress(
    seq,
    max_repeat_len=4,
  )

  print(''.join(seq))

  for atom in solved.atoms:
    print(''.join(map(str, atom.keys)), end='')
    print('-' * len(atom.keys) * (atom.repeat - 1), end='')
