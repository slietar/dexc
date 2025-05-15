from typing import Callable, Sequence, TypeVar

from . import Atom, Solution


T = TypeVar('T')
S = TypeVar('S')

def compress(
  items: Sequence[T],
  /,
  *,
  backwards: bool = False,
  key: Callable[[T], S] = (lambda item: item),
  max_repeat_len: int = 10,
) -> Solution[T, S]:
  if backwards:
    atoms = compress(items[::-1], key=key, max_repeat_len=max_repeat_len)

    return [Atom(
      keys=atom.keys[::-1],
      realization=atom.realization[::-1],
      repeat_count=atom.repeat_count,
    ) for atom in reversed(atoms)]

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
      repeat_count=repeat,
    ))

    index += repeat_len * repeat

  return atoms
