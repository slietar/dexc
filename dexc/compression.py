import functools
import random
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class Atom[T, S]:
  keys: tuple[S, ...]
  realization: list[T]
  repeat: int

type Solution[T, S] = list[Atom[T, S]]

@dataclass(slots=True)
class MeasuredSolution[T, S]:
  atoms: Solution[T, S]
  cost: float

def compress[T, S](
  original_items: list[T],
  /,
  *,
  key: Callable[[T], S] = (lambda item: item),
  repeat_cost: Callable[[int], float] = (lambda repeat: 0.0 * repeat),
):
  @functools.cache
  def solve(start_index: int, end_index: int) -> MeasuredSolution[T, S]:
    items = original_items[start_index:end_index]

    if len(items) == 0:
      return MeasuredSolution([], 0.0)
    if len(items) == 1:
      return MeasuredSolution([Atom(
        keys=(key(items[0]),),
        realization=[items[0]],
        repeat=1,
      )], 1.0)

    solutions = list[MeasuredSolution[T, S]]()

    for split_index in range(1, len(items)):
      left = items[:split_index]
      right = items[split_index:]

      left_sol = solve(start_index, start_index + split_index)
      right_sol = solve(start_index + split_index, end_index)

      solutions.append(MeasuredSolution(
        [*left_sol.atoms, *right_sol.atoms],
        left_sol.cost + right_sol.cost,
      ))

      # print(f'{list(left)} + {list(right)}')

      left_keys = tuple(map(key, left))
      right_keys = tuple(map(key, right))

      if left_keys == right_keys:
        solutions.append(MeasuredSolution(
          [Atom(keys=left_keys, realization=(left + right), repeat=2)],
          len(left) * (1.0 + repeat_cost(1)),
        ))

      last_left_atom = left_sol.atoms[-1]

      if last_left_atom.keys == right_keys:
        new_repeat = last_left_atom.repeat + 1
        solutions.append(MeasuredSolution(
          [*left_sol.atoms[:-1], Atom(keys=right_keys, realization=(last_left_atom.realization + right), repeat=new_repeat)],
          left_sol.cost + (repeat_cost(new_repeat - 1) - repeat_cost(last_left_atom.repeat - 1)) * len(right),
        ))

    return min(solutions, key=(lambda sol: sol.cost))

  return solve(0, len(original_items))


if __name__ == '__main__':
  # print(solve((3, 4, 2, 2, 3, 4, 3, 4, 5)))
  # print(solve(tuple([random.randint(0, 3) for _ in range(50)])))

  seq = [random.randint(0, 1) for _ in range(100)]
  # seq = list('22222210010122113333030111123333303200112330322320')
  seq = list('132123131')
  solved = compress(seq, key=lambda x: min(x, '2'))
  print(f'Cost: {solved.cost}')

  print(''.join(map(str, seq)))

  for atom in solved.atoms:
    print(''.join(map(str, atom.keys)) * atom.repeat, end='')

  print()

  for atom in solved.atoms:
    print(''.join(map(str, atom.keys)), end='')
    print('-' * len(atom.keys) * (atom.repeat - 1), end='')
    # print(''.join(map(str, subseq)) * count, end='')

  print()
