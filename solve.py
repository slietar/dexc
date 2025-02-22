# def find_repeated_subsequences(lst, k):
#     seen = set()
#     repeated = set()

#     for i in range(len(lst) - k + 1):
#         sub = tuple(lst[i:i + k])  # Convert sublist to tuple (since lists are unhashable)
#         if sub in seen:
#             repeated.add(sub)
#         else:
#             seen.add(sub)

#     return list(repeated)

# # Example usage
# lst = [1, 2, 3, 4, 3, 4, 1, 5]
# k = 1  # Length of the repeating group
# print(find_repeated_subsequences(lst, k))


import functools
import random
from typing import Sequence


def find_repeated_subsequences[T](items: list[T], /):
  for index, item in enumerate(items):
    # split_index includes the start of the repeat
    # for split_index in range(index + 1, len(items)):
    #   subsequence_length = index - split_index + 1
    #   subsequence_original = items[(split_index - subsequence_length):split_index]
    #   subsequence_repeat = items[split_index:(index + 1)]

    #   #    index - split_index + 1 > 0
    #   # => split_index < index + 1

    for subs_length in range((index + 1) // 2, 0, -1):
    # for subs_length in range(1, (index + 1) // 2 + 1):
      subs_original = items[(index - subs_length * 2 + 1):(index - subs_length + 1)]
      subs_repeated = items[(index - subs_length + 1):(index + 1)]

      if subs_original == subs_repeated:
        print(items[:(index+1)], subs_length, subs_original, subs_repeated)

    print('-')

#                                 0  1  2  3  4  5
# print(find_repeated_subsequences([1, 3, 4, 3, 4, 5]))
# print(find_repeated_subsequences([3, 4, 3, 4, 5,  3, 4, 3, 4, 5]))


# [3, 4, 3, 4, 5,  3, 4, 3, 4, 5]

# [3, 4, Repeat(2), 5]
# [3, 4, 3, 4, 5, Repeat(5)]


type Solution[T] = list[tuple[tuple[T, ...], int]]
type WeightedSolution[T] = tuple[Solution[T], float]

@functools.cache
def solve[T](items: tuple[T, ...]) -> WeightedSolution[T]:
  # print(items)

  if len(items) == 0:
    return [], 0.0
  if len(items) == 1:
    return [(items, 1)], 1.0

  solutions = list[WeightedSolution[T]]()

  for split_index in range(1, len(items)):
    left = items[:split_index]
    right = items[split_index:]

    left_sol, left_cost = solve(left)
    right_sol, right_cost = solve(right)

    solutions.append((
      [*left_sol, *right_sol],
      left_cost + right_cost,
    ))

    if left == right:
      solutions.append((
        [(left, 2)],
        len(left) * 1.1,
      ))

    if left_sol[-1][0] == right:
      solutions.append((
        [*left_sol[:-1], (right, left_sol[-1][1] + 1)],
        left_cost + 0.1 * len(right),
      ))

  return min(solutions, key=(lambda x: x[1]))


# print(solve((3, 4, 2, 2, 3, 4, 3, 4, 5)))
# print(solve(tuple([random.randint(0, 3) for _ in range(50)])))

seq = [random.randint(0, 3) for _ in range(50)]
print(''.join(map(str, seq)))

for subseq, count in solve(tuple(seq))[0]:
  print(''.join(map(str, subseq)) * count, end='')

print()

for subseq, count in solve(tuple(seq))[0]:
  print(''.join(map(str, subseq)), end='')
  print('-' * len(subseq) * (count - 1), end='')
  # print(''.join(map(str, subseq)) * count, end='')
