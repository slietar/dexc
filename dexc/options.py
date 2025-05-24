import shutil
from dataclasses import dataclass
from typing import Optional


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

  def get_width(self):
    if self.width is not None:
      width = self.width
    else:
      width, _ = shutil.get_terminal_size((self.max_width, 24))

    return max(min(width, self.max_width), 40)
