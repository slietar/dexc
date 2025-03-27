from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional, TypedDict


OPTIONS_RELATIVE_PATH = '.config/dexc/options.json'
OPTIONS_ABSOLUTE_PATH = Path.home() / OPTIONS_RELATIVE_PATH


@dataclass(kw_only=True, slots=True)
class Options:
  ascii_only: bool = False
  chain_origin_on_top: bool = False
  colorize: Optional[bool] = None
  compression_first_on_top: bool = False
  inner_frame_on_top: bool = False
  max_context_lines_after: int = 2
  max_context_lines_before: int = 3
  max_target_lines: int = 5
  skip_indentation_highlight: bool = True
  remove_common_indentation: bool = True

  @classmethod
  def load(cls, other_dict: dict = {}):
    if OPTIONS_ABSOLUTE_PATH.exists():
      try:
        with OPTIONS_ABSOLUTE_PATH.open() as options_file:
          options_dict = json.load(options_file)

        return cls(**(options_dict | other_dict)), None
      except Exception as e:
        return cls(**other_dict), f'Failed to load options: {e}'

    return cls(**other_dict), None

class OptionsDict(TypedDict):
  ascii_only: bool
  chain_origin_on_top: bool
  colorize: Optional[bool]
  compression_first_on_top: bool
  inner_frame_on_top: bool
  max_context_lines_after: int
  max_context_lines_before: int
  max_target_lines: int
  skip_indentation_highlight: bool
  remove_common_indentation: bool
