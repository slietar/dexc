import functools
from pprint import pprint
import random
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


@dataclass(slots=True)
class Atom[T, S]:
  keys: tuple[S, ...]
  realization: Sequence[T]
  repeat: int

type Solution[T, S] = list[Atom[T, S]]

@dataclass(slots=True)
class MeasuredSolution[T, S]:
  atoms: Solution[T, S]
  cost: float

def compress_optimal[T, S](
  all_items: list[T],
  /,
  *,
  key: Callable[[T], S] = (lambda item: item),
  repeat_cost: Callable[[int], float] = (lambda repeat: 0.0 * repeat),
):
  all_keys = list(map(key, all_items))

  # if len(set(keys)) == len(keys):
  #   return MeasuredSolution([Atom(
  #     keys=(item_key,),
  #     realization=[item],
  #     repeat=1,
  #   ) for item, item_key in zip(original_items, keys)], len(original_items))

  # key_counts = {key: 0 for key in keys}

  v = 0

  a = 0
  b = 0

  @functools.cache
  def solve(start_index: int, end_index: int) -> MeasuredSolution[T, S]:
    items = all_items[start_index:end_index]

    # print(v)

    if len(items) == 0:
      return MeasuredSolution([], 0.0)

    if len(items) == 1:
      return MeasuredSolution([Atom(
        keys=(key(items[0]),),
        realization=[items[0]],
        repeat=1,
      )], 1.0)

    keys = all_keys[start_index:end_index]
    unique_keys = set(keys)
    # print('>', keys, unique_keys)

    if len(unique_keys) == len(keys) and 1:
      # print('skip', keys)
      return MeasuredSolution([Atom(
        keys=tuple(keys),
        realization=items,
        repeat=1,
      )], len(items))

    if len(unique_keys) == 1:
      return MeasuredSolution([Atom(
        keys=tuple(unique_keys),
        realization=items,
        repeat=2,
      )], len(items))


    nonlocal a, b, v
    v += 1


    solutions = list[MeasuredSolution[T, S]]()
    key_counts = {key_: 0 for key_ in unique_keys}

    for key_ in keys:
      key_counts[key_] += 1

    current_key_counts = {key_: 0 for key_ in unique_keys}
    inverse_key_counts = key_counts.copy()

    for split_index in range(1, len(items)):
      current_key_counts[keys[split_index - 1]] += 1
      inverse_key_counts[keys[split_index - 1]] -= 1


    for split_index in range(1, len(items)):
      left_items = items[:split_index]
      right_items = items[split_index:]

      left_sol = solve(start_index, start_index + split_index)
      right_sol = solve(start_index + split_index, end_index)

      solutions.append(MeasuredSolution(
        [*left_sol.atoms, *right_sol.atoms],
        left_sol.cost + right_sol.cost,
      ))

      # left_keys = tuple(all_keys[start_index:(start_index + split_index)])
      # right_keys = tuple(all_keys[(start_index + split_index):end_index])
      left_keys = tuple(keys[:split_index])
      right_keys = tuple(keys[split_index:])

      # print(f'{list(left_keys)} + {list(right_keys)}')

      if left_keys == right_keys:
        a += 1
        solutions.append(MeasuredSolution(
          [Atom(keys=left_keys, realization=(left_items + right_items), repeat=2)],
          len(left_items) * (1.0 + repeat_cost(1)),
        ))

      last_left_atom = left_sol.atoms[-1]

      if last_left_atom.keys == right_keys:
        b += 1
        new_repeat = last_left_atom.repeat + 1
        solutions.append(MeasuredSolution(
          [*left_sol.atoms[:-1], Atom(keys=right_keys, realization=(last_left_atom.realization + right_items), repeat=new_repeat)],
          left_sol.cost + (repeat_cost(new_repeat - 1) - repeat_cost(last_left_atom.repeat - 1)) * len(right_items),
        ))

    return min(solutions, key=(lambda sol: sol.cost))

  r = solve(0, len(all_items))

  print('>>>', v)
  print('>>>', a)
  print('>>>', b)

  return r


def find_repeats[T](items: list[T]):
  locations = dict[T, list[int]]()
  repeats = dict[int, list[int]]()

  for index, item in enumerate(items):
    index_locations = locations.setdefault(item, [])

    for location in index_locations:
      if items[location:index] == items[index:(index * 2 - location)]:
        repeats.setdefault(location, []).append(index - location)

    index_locations.append(index)

  return repeats


def find_repeats_max_size[T](items: list[T], *, max_repeat_len: int = 10):
  repeats = dict[int, list[int]]()

  for index, item in enumerate(items):
    for location in range(max(0, index - max_repeat_len), index):
      if items[location:index] == items[index:(index * 2 - location)]:
        repeats.setdefault(location, []).append(index - location)

  return repeats


def merge_repeats(repeats: dict[int, list[int]]):
  merged_repeats = list[tuple[int, int, int]]()

  for index, repeat_lens in repeats.items():
    for repeat_len in repeat_lens:
      repeat = 2

      while repeat_len in repeats.get(index + repeat_len * (repeat - 1), []):
        repeat += 1

      merged_repeats.append((index, repeat_len, repeat))

  return merged_repeats


def compress_fast[T, S](
  all_items: list[T],
  /,
  *,
  key: Callable[[T], S] = (lambda item: item),
):
  keys = list(map(key, all_items))

  # locations = dict[S, list[int]]()
  # repeats = dict[int, list[int]]()

  # for index, key_ in enumerate(keys):
  #   for location in locations.get(key_, []):
  #     if keys[location:index] == keys[index:(index * 2 - location)]:
  #       repeats.setdefault(location, []).append(index - location)

  #   locations.setdefault(key_, []).append(index)

  repeats = find_repeats_max_size(keys)
  # print('unmerged', list(repeats.items()))
  # print('merged', merge_repeats(repeats))
  # print('ok')

  atoms = list[Atom[T, S]]()
  index = 0

  while index < len(all_items):
    key_ = keys[index]
    index_repeats = repeats.get(index)

    if index_repeats:
      atom_len = max(index_repeats)
      repeat = 2

      while max(repeats.get(index + atom_len * (repeat - 1), [0])) == atom_len:
        repeat += 1

      atoms.append(Atom(
        keys=tuple(keys[index:(index + atom_len)]),
        realization=all_items[index:(index + atom_len * repeat)],
        repeat=repeat,
      ))

      index += atom_len * repeat
    else:
      atoms.append(Atom(
        keys=(key_,),
        realization=[all_items[index]],
        repeat=1,
      ))

      index += 1

  return MeasuredSolution(atoms, cost=0.0)


compress = compress_fast


__all__ = [
  'compress',
]


if __name__ == '__main__':
  # print(solve((3, 4, 2, 2, 3, 4, 3, 4, 5)))
  # print(solve(tuple([random.randint(0, 3) for _ in range(50)])))

  # seq = [random.randint(0, 9) for _ in range(10000)]
  # seq = list('22222210010122113333030111123333303200112330322320')
  # seq = list('12123123123')
  # seq = list('2345111116789')
  seq = list('1' * 10)

  # pprint(compress_fast(seq, key=lambda x: x))

  # solved = compress_optimal(seq)
  solved = compress_fast(seq)
  # print(f'Cost: {solved.cost}')
  # print(''.join(map(str, seq)))

  # for atom in solved.atoms:
  #   print(''.join(map(str, atom.keys)) * atom.repeat, end='')

  # print()

  for atom in solved.atoms:
    print(''.join(map(str, atom.keys)), end='')
    print('-' * len(atom.keys) * (atom.repeat - 1), end='')
    # print(''.join(map(str, subseq)) * count, end='')

  # print()
