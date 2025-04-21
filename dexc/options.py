import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict


OPTIONS_RELATIVE_PATH = '.config/dexc/options.json'
OPTIONS_ABSOLUTE_PATH = Path.home() / OPTIONS_RELATIVE_PATH


@dataclass(kw_only=True, slots=True)
class Options:
  aggregate_nonuser_frames: bool = True
  ascii_only: bool = False
  chain_origin_on_top: bool = False
  colorize: Optional[bool] = None
  compression_first_on_top: bool = False
  display_internal_frames: bool = False
  generic_indent: int = 2
  include_module_name_in_frames: bool = False
  inner_frame_on_top: bool = False
  max_context_lines_after: int = 2
  max_context_lines_before: int = 3
  max_target_lines: int = 5
  max_traces: int = 3
  max_width: int = 100
  remove_common_indentation: bool = True
  render_links: Optional[bool] = None
  skip_indentation_highlight: bool = True
  width: Optional[int] = None

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

  def get_width(self):
    if self.width is not None:
      width = self.width
    else:
      width, _ = shutil.get_terminal_size((self.max_width, 24))

    return min(width, self.max_width)

class OptionsDict(TypedDict):
  aggregate_nonuser_frames: bool
  ascii_only: bool
  chain_origin_on_top: bool
  colorize: Optional[bool]
  compression_first_on_top: bool
  display_internal_frames: bool
  generic_indent: int
  include_module_name_in_frames: bool
  inner_frame_on_top: bool
  max_context_lines_after: int
  max_context_lines_before: int
  max_target_lines: int
  max_traces: int
  skip_indentation_highlight: bool
  remove_common_indentation: bool
  target_links: bool
