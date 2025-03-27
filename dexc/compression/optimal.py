import functools
from dataclasses import dataclass
from typing import Callable

from . import Atom, Solution


@dataclass(slots=True)
class MeasuredSolution[T, S]:
  atoms: Solution[T, S]
  cost: float

def compress[T, S](
  all_items: list[T],
  /,
  *,
  key: Callable[[T], S] = (lambda item: item),
  repeat_cost: Callable[[int], float] = (lambda repeat: 0.0 * repeat),
):
  all_keys = list(map(key, all_items))

  @functools.cache
  def solve(start_index: int, end_index: int) -> MeasuredSolution[T, S]:
    items = all_items[start_index:end_index]

    if len(items) == 0:
      return MeasuredSolution([], 0.0)

    if len(items) == 1:
      return MeasuredSolution([Atom(
        keys=(key(items[0]),),
        realization=[items[0]],
        repeat_count=1,
      )], 1.0)

    keys = all_keys[start_index:end_index]
    unique_keys = set(keys)

    if len(unique_keys) == len(keys):
      return MeasuredSolution([Atom(
        keys=tuple(keys),
        realization=items,
        repeat_count=1,
      )], len(items))

    if len(unique_keys) == 1:
      return MeasuredSolution([Atom(
        keys=tuple(unique_keys),
        realization=items,
        repeat_count=len(keys),
      )], len(items))


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
        solutions.append(MeasuredSolution(
          [Atom(keys=left_keys, realization=(left_items + right_items), repeat_count=2)],
          len(left_items) * (1.0 + repeat_cost(1)),
        ))

      last_left_atom = left_sol.atoms[-1]

      if last_left_atom.keys == right_keys:
        new_repeat = last_left_atom.repeat_count + 1
        solutions.append(MeasuredSolution(
          [*left_sol.atoms[:-1], Atom(keys=right_keys, realization=(list(last_left_atom.realization) + right_items), repeat_count=new_repeat)],
          left_sol.cost + (repeat_cost(new_repeat - 1) - repeat_cost(last_left_atom.repeat_count - 1)) * len(right_items),
        ))

    return min(solutions, key=(lambda sol: sol.cost))

  return solve(0, len(all_items)).atoms
