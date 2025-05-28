from dataclasses import dataclass
from typing import Generic, Sequence, TypeAlias, TypeVar


T = TypeVar('T')
S = TypeVar('S')

@dataclass(slots=True)
class Atom(Generic[T, S]):
  keys: tuple[S, ...]
  realization: Sequence[T]
  repeat_count: int

Solution: TypeAlias = list[Atom[T, S]]
