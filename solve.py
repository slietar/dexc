import functools
import random
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(slots=True)
class Atom[T]:
  value: tuple[T, ...]
  repeat: int

type Solution[T] = list[Atom]

@dataclass(slots=True)
class MeasuredSolution[T]:
  atoms: Solution[T]
  cost: float

def solve[T](
  items: Iterable[T],
  /,
  *,
  repeat_cost: Callable[[int], float] = (lambda repeat: 0.0 * repeat),
):
  @functools.cache
  def solve(items: tuple[T, ...]) -> MeasuredSolution[T]:
    if len(items) == 0:
      return MeasuredSolution([], 0.0)
    if len(items) == 1:
      return MeasuredSolution([Atom(items, 1)], 1.0)

    solutions = list[MeasuredSolution[T]]()

    for split_index in range(1, len(items)):
      left = items[:split_index]
      right = items[split_index:]

      left_sol = solve(left)
      right_sol = solve(right)

      solutions.append(MeasuredSolution(
        [*left_sol.atoms, *right_sol.atoms],
        left_sol.cost + right_sol.cost,
      ))

      # print(f'{list(left)} + {list(right)}')

      if left == right:
        solutions.append(MeasuredSolution(
          [Atom(left, 2)],
          len(left) * (1.0 + repeat_cost(1)),
        ))

      last_left_atom = left_sol.atoms[-1]

      if last_left_atom.value == right:
        new_repeat = last_left_atom.repeat + 1
        solutions.append(MeasuredSolution(
          [*left_sol.atoms[:-1], Atom(right, new_repeat)],
          left_sol.cost + (repeat_cost(new_repeat - 1) - repeat_cost(last_left_atom.repeat - 1)) * len(right),
        ))

    return min(solutions, key=(lambda sol: sol.cost))

  return solve(tuple(items))


if __name__ == '__main__':
  # print(solve((3, 4, 2, 2, 3, 4, 3, 4, 5)))
  # print(solve(tuple([random.randint(0, 3) for _ in range(50)])))

  seq = [random.randint(0, 1) for _ in range(100)]
  # seq = list('22222210010122113333030111123333303200112330322320')
  seq = list('12121212')
  solved = solve(tuple(seq))
  print(f'Cost: {solved.cost}')

  print(''.join(map(str, seq)))

  for atom in solved.atoms:
    print(''.join(map(str, atom.value)) * atom.repeat, end='')

  print()

  for atom in solved.atoms:
    print(''.join(map(str, atom.value)), end='')
    print('-' * len(atom.value) * (atom.repeat - 1), end='')
    # print(''.join(map(str, subseq)) * count, end='')

  print()
