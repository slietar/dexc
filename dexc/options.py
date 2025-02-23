from dataclasses import dataclass
from typing import Optional, TypedDict


@dataclass(kw_only=True, slots=True)
class Options:
  ascii_only: bool = False
  chain_origin_on_top: bool = False
  colorize: Optional[bool] = True
  inner_frame_on_top: bool = False
  max_context_lines_after: int = 2
  max_context_lines_before: int = 3
  max_target_lines: int = 5
  skip_indentation_highlight: bool = True
  remove_common_indentation: bool = True

class OptionsDict(TypedDict):
  ascii_only: bool
  chain_origin_on_top: bool
  colorize: Optional[bool]
  inner_frame_on_top: bool
  max_context_lines_after: int
  max_context_lines_before: int
  max_target_lines: int
  skip_indentation_highlight: bool
  remove_common_indentation: bool
