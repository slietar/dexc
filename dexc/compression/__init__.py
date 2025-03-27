from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class Atom[T, S]:
  keys: tuple[S, ...]
  realization: Sequence[T]
  repeat_count: int

type Solution[T, S] = list[Atom[T, S]]
