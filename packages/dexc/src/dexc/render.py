import os
import sys
from dataclasses import dataclass, field
from pprint import pprint
from typing import (IO, Any, Container, Generator, Iterable, Literal, Optional,
                    Sequence, TypeAlias)

from . import util
from .compression import Atom
from .compression.greedy import compress
from .extract import (ExceptionChain, FrameAreaFull, FrameAreaLines,
                      FrameAreaStartLine, FrameAreaStartLineCol, FrameItem,
                      ModuleInfo)
from .options import Options
from .util import UnreachableError, reversed_if
from .vendor import get_ipython


@dataclass(slots=True)
class Symbols:
  color_bold: str
  color_bright_black: str
  color_italic: str
  color_orange: str
  color_red: str
  color_reset: str
  color_yellow: str
  underline: str
  underline_reset: str

  box_down_left: str
  box_down_right: str
  box_horizontal: str
  box_up_left: str
  box_up_right: str
  box_vertical_right: str
  box_vertical: str

  chevron_right: str
  ellipsis: str
  link_enabled: bool

  def __init__(self, *, ascii_only: bool, colorize: bool, render_links: bool):
    if ascii_only:
      self.box_down_left = '+'
      self.box_down_right = '+'
      self.box_horizontal = '-'
      self.box_up_left = '+'
      self.box_up_right = '+'
      self.box_vertical = '|'
      self.box_vertical_right = '+'

      self.chevron_right = '>'
      self.ellipsis = '...'
    else:
      self.box_down_left = '\u2510'
      self.box_down_right = '\u250c'
      self.box_horizontal = '─'
      self.box_up_left = '\u2518'
      self.box_up_right = '\u2514'
      self.box_vertical = '\u2502'
      self.box_vertical_right = '\u251c'

      self.chevron_right = '\u203a'
      self.ellipsis = '\u2026'

    if colorize:
      self.color_bold = '\033[1m'
      self.color_bright_black = '\033[90m'
      self.color_italic = '\033[3m'
      self.color_orange = '\033[38;5;208m'
      self.color_red = '\033[31m'
      self.color_reset = '\033[0m'
      self.color_yellow = '\033[33m'
      self.underline = '\033[4m'
      self.underline_reset = '\033[24m'
    else:
      self.color_bold = ''
      self.color_bright_black = ''
      self.color_italic = ''
      self.color_orange = ''
      self.color_red = ''
      self.color_reset = ''
      self.color_yellow = ''
      self.underline = ''
      self.underline_reset = ''

    self.link_enabled = render_links

  # Line number starts at 1
  # Column number starts at 0
  def link(self, text: str, url: str, *, column_number: Optional[int] = None, line_number: Optional[int] = None):
    assert (column_number is None) or (line_number is not None)

    if not self.link_enabled:
      return text

    full_url = (
        url
      + (f'#{line_number}' if line_number is not None else '')
      + (f':{column_number + 1}' if column_number is not None else '')
    )

    return f'\033]8;;{full_url}\033\\{text}\033]8;;\033\\'

  @classmethod
  def from_file(cls, file: IO[str], options: Options):
    no_color = os.environ.get('NO_COLOR')

    if no_color:
      colorize = False
    elif os.environ.get('FORCE_COLOR'):
      colorize = True
    elif options.colorize is not None:
      colorize = options.colorize
    else:
      colorize = (
        file.isatty() or (
          (file == sys.stderr) and
          (get_ipython() is not None)
        )
      )

    if no_color:
      render_links = False
    elif options.render_links is not None:
      render_links = options.render_links
    else:
      render_links = colorize and ('TERM_PROGRAM' in os.environ)

    return cls(
      ascii_only=options.ascii_only,
      colorize=colorize,
      render_links=render_links,
    )


@dataclass(slots=True)
class LibraryFrameAggregate:
  package_name: str
  frames: list[FrameItem] = field(default_factory=list)

AggregatedFrame: TypeAlias = FrameItem | LibraryFrameAggregate

def aggregate_frames(frames: Iterable[FrameItem], options: Options):
  aggregated_frames = list[AggregatedFrame]()

  for frame in frames:
    match frame.module:
      case ModuleInfo(kind='internal') if not options.display_internal_frames:
        pass
      case ModuleInfo(kind=('internal' | 'lib' | 'std'), name_segments=[package_name, *_]) if options.aggregate_nonuser_frames:
        if not (aggregated_frames and isinstance(aggregated_frames[-1], LibraryFrameAggregate) and (aggregated_frames[-1].package_name == package_name)):
          aggregated_frames.append(LibraryFrameAggregate(package_name=package_name))

        aggregated_frames[-1].frames.append(frame) # type: ignore
      case ModuleInfo():
        aggregated_frames.append(frame)
      case _:
        raise UnreachableError

  return aggregated_frames


RenderProfile: TypeAlias = Literal['default', 'warning']

def render(
  chain: ExceptionChain,
  file: IO[str],
  options: Options,
  prefix: str = '',
  profile: RenderProfile = 'default',
  suffix: str = '',
  width: Optional[int] = None, # Excluding prefix and suffix
  _symbols: Optional[Symbols] = None,
):
  width_ = options.get_width() if width is None else width

  file.write(prefix)

  debug = False
  newline_required = False
  symbols = _symbols if _symbols is not None else Symbols.from_file(file, options)

  for line_index, (line, line_len) in enumerate(render_item(
    chain,
    options,
    floating=False,
    profile=profile,
    symbols=symbols,
    width=width_,
    width_first=width_,
  )):
    if newline_required:
      file.write(prefix)

      if debug or suffix:
        file.write(symbols.color_bright_black + ('·' if debug else ' ') * width_ + symbols.color_reset)
        file.write(suffix)

      file.write('\n')
      newline_required = False

    if not line:
      newline_required = True
      continue

    if line_index > 0:
      file.write(prefix)

    file.write(line)

    if debug or suffix:
      file.write(symbols.color_bright_black + ('·' if debug else ' ') * (width_ - line_len) + symbols.color_reset)
      file.write(suffix)

    file.write('\n')


def render_item(
  chain: ExceptionChain,
  options: Options,
  *,
  floating: bool,
  profile: RenderProfile,
  symbols: Symbols,
  width: int,
  width_first: int,
): # -> Generator[tuple[str, int]]:
  generic_indent_str = options.generic_indent * ' '
  newline_required = False

  for item, relation in (
    zip(chain.items[::-1], [None, *chain.relations[::-1]])
    if options.chain_origin_on_top
    else zip(chain.items, [None, *chain.relations])
  ):
    if newline_required:
      yield '', 0
      newline_required = False

    # Relation

    if relation is not None:
      yield '', 0

      match relation:
        case 'cause':
          relation_message = 'Causing' if options.chain_origin_on_top else 'Caused by'
        case 'context':
          relation_message = 'Raising while handling' if options.chain_origin_on_top else 'Raised while handling'
        case _:
          raise UnreachableError

      relation_line = f'[{relation_message}]'

      yield symbols.color_italic + relation_line + symbols.color_reset, len(relation_line)
      yield '', 0


    # Description

    if item.children:
      current_prefix = symbols.box_vertical
      current_indent = ' ' * max(options.generic_indent - 2, 1)
    elif not floating:
      current_prefix = ''
      current_indent = generic_indent_str
    else:
      current_prefix = ''
      current_indent = ''

    current_width = width - len(current_prefix) - len(current_indent)

    if isinstance(item.instance, SyntaxError):
      desc = item.instance.args[0]
    else:
      desc = str(item.instance)

    desc_lines = desc.splitlines() if desc else []

    exc_type_name = util.wrap_into_ellipsis(type(item.instance).__name__, ellipsis=symbols.ellipsis, width=width)
    exc_type_sep = ': '

    if desc_lines and (len(desc_lines[0]) <= width_first - len(exc_type_name) - len(exc_type_sep)):
      yield (
        symbols.color_bold + exc_type_name + exc_type_sep + symbols.color_reset + desc_lines[0],
        len(exc_type_name) + len(exc_type_sep) + len(desc_lines[0]),
      )

      body_lines = desc_lines[util.lcount_lines_until_nonempty(desc_lines, start=1):]
    else:
      yield (
        symbols.color_bold + exc_type_name + symbols.color_reset,
        len(exc_type_name),
      )

      body_lines = desc_lines

    if body_lines:
      desc_exp_add_indent = generic_indent_str if (not item.children) and floating else ''
      desc_exp_width = current_width - len(desc_exp_add_indent)

      for body_line in body_lines:
        for wrapped_line, wrapped_line_len in util.wrap_into_paragraph(body_line, link=symbols.link, width=desc_exp_width):
          yield (
              current_prefix
            + current_indent
            + desc_exp_add_indent
            + wrapped_line,

              len(current_prefix)
            + len(current_indent)
            + len(desc_exp_add_indent)
            + wrapped_line_len,
          )

        newline_required = True


    # Notes

    notes: list[str] = getattr(item.instance, '__notes__', [])
    note_width = current_width

    note_header_str = 'note'
    note_prefix = current_prefix + current_indent

    for note in notes:
      note_lines = note.splitlines()

      # Remove empty lines
      note_line_start_index = util.lcount_lines_until_nonempty(note_lines)

      # Remove separator e.g. used by Jax
      if note_lines[note_line_start_index] == '-' * len(note_lines[note_line_start_index]):
        note_line_start_index += 1

      # Remove empty lines
      note_line_start_index = util.lcount_lines_until_nonempty(note_lines, start=note_line_start_index)

      note_lines_trunc = note_lines[note_line_start_index:]
      # note_lines_trunc = note_lines

      if newline_required:
        yield current_prefix, len(current_prefix)

      note_header = note_prefix + symbols.color_bold + note_header_str + symbols.color_reset
      note_header_len = len(note_prefix) + len(note_header_str)

      if (len(note_lines_trunc) == 1) and (len(note_lines_trunc[0]) <= note_width):
        yield (
          f'{note_header} {note_lines_trunc[0]}',
          note_header_len + 1 + len(note_lines_trunc[0]),
        )

        newline_required = False
      else:
        note_exp_add_indent = generic_indent_str

        yield note_header, note_header_len

        for note_line in note_lines_trunc:
          for wrapped_line, wrapped_line_len in util.wrap_into_paragraph(note_line, width=(note_width - len(note_exp_add_indent))):
            yield (
              note_prefix + note_exp_add_indent + wrapped_line,
              len(note_prefix) + len(note_exp_add_indent) + wrapped_line_len,
            )

        newline_required = True

    if notes:
      newline_required = True


    # Frames

    if item.frames:
      if newline_required:
        yield current_prefix, len(current_prefix)
        newline_required = False

      # Reversing here so we don't have to reverse every atom later on
      frames = util.reversed_if(item.frames, options.inner_frame_on_top)

      aggregated_frames = aggregate_frames(frames, options)
      atoms = compress(aggregated_frames, backwards=(not options.compression_first_on_top))
      # pprint(aggregated_frames)

      trace_indices = set[tuple[int, int]]()

      for atom_inner_index, (atom_display_index, atom) in enumerate(util.reversed_if(list(enumerate(atoms)), not options.inner_frame_on_top)):
        for agg_frame_index, agg_frame in util.reversed_if(list(enumerate(atom.realization[:len(atom.keys)])), not options.inner_frame_on_top):
          if isinstance(agg_frame, FrameItem) and agg_frame.important and agg_frame.traceable and (len(trace_indices) < options.max_traces):
            trace_indices.add((atom_display_index, agg_frame_index))

      frame_indent = current_indent

      for frame_line, frame_line_len in render_frames(
        atoms,
        options,
        indent=frame_indent,
        profile=profile,
        symbols=symbols,
        trace_indices=trace_indices,
        width=current_width,
      ):
        if newline_required:
          yield current_prefix, len(current_prefix)
          newline_required = False

        if not frame_line:
          newline_required = True
          continue

        yield (
          current_prefix + frame_line,
          len(current_prefix) + frame_line_len,
        )


    # Children

    for child_index, child in enumerate(item.children):
      if newline_required:
        yield current_prefix, len(current_prefix)
        newline_required = False

      is_child_last = child_index == len(item.children) - 1
      child_prefix, child_indent = ('', '    ') if is_child_last else (symbols.box_vertical, '   ')

      child_prefix_first = (symbols.box_up_right if is_child_last else symbols.box_vertical_right) + symbols.box_horizontal * 2
      child_indent_first = ' '

      for child_line_index, (child_line, child_line_len) in enumerate(render_item(
        child,
        options,
        floating=True,
        profile=profile,
        symbols=symbols,
        width=(width - len(child_prefix) - len(child_indent)),
        width_first=(width - len(child_prefix_first) - len(child_indent_first)),
      )):
        if newline_required:
          yield child_prefix, len(child_prefix)
          newline_required = False

        if not child_line:
          newline_required = True
          continue

        if child_line_index == 0:
          yield (
            child_prefix_first + child_indent_first + child_line,
            len(child_prefix_first) + len(child_indent_first) + child_line_len,
          )
        else:
          if child_line_len > 0:
            yield (
              child_prefix + child_indent + child_line,
              len(child_prefix) + len(child_indent) + child_line_len,
            )
          else:
            yield child_prefix, len(child_prefix)

  if newline_required:
    yield '', 0


def render_frames(
  atoms: Sequence[Atom[AggregatedFrame, Any]],
  options: Options,
  *,
  indent: str,
  profile: RenderProfile,
  symbols: Symbols,
  trace_indices: Container[tuple[int, int]],
  width: int, # Excluding indent
): # -> Generator[tuple[str, int]]: # Both including indent
  # Additional options
  generic_indent_str = options.generic_indent * ' '
  inset_repeat_box = True
  skip_newline_on_highlights_at_trace_ends = True

  most_width = max(width - 20, width * 7 // 10)

  # Whether a newline is required before the next frame
  newline_required = False

  for atom_index, atom in enumerate(atoms):
    # atom_correct_index = atom_index if options.inner_frame_on_top else len(atoms) - atom_index - 1
    repeat_box = (atom.repeat_count > 1) and (len(atom.keys) > 1)

    if repeat_box and (atom_index > 0):
      newline_required = True

    if newline_required:
      yield '', 0
      newline_required = False

    if repeat_box:
      if inset_repeat_box and (indent[-2:] == generic_indent_str):
        repeat_box_indent = indent[:-2]
      else:
        repeat_box_indent = indent

      repeat_box_header = f'{repeat_box_indent}{symbols.box_down_right}{symbols.box_horizontal * 2} Repeated {atom.repeat_count} times {symbols.box_horizontal * 2}'
      yield repeat_box_header, len(repeat_box_header)

      frame_prefix = repeat_box_indent + symbols.box_vertical
      frame_indent = ' '
    else:
      frame_prefix = ''
      frame_indent = indent
      repeat_box_indent = None

    width_diff = len(indent) - len(frame_prefix) - len(frame_indent)
    available_width = width + width_diff
    most_available_width = most_width + width_diff

    for agg_frame_index, agg_frame in enumerate(atom.realization[:len(atom.keys)]):
      if newline_required:
        yield frame_prefix, len(frame_prefix)

      match agg_frame:
        case FrameItem():
          frame: FrameItem = agg_frame


          # Frame left title

          frame_title_color = symbols.color_bright_black if not frame.important else ''

          frame_title_left = 'at '
          frame_title_left_len = len(frame_title_left)

          title_left_suffix = ''

          if frame.reraise:
            title_left_suffix += ' [re-raise]'

          if (atom.repeat_count > 1) and (len(atom.keys) == 1):
            title_left_suffix += f' [repeated {atom.repeat_count} times]'

          frame_title_left_len += len(title_left_suffix)


          emphasize_last = False
          target_path = list[str]()

          if options.include_module_name_in_frames and (frame.module.name_segments is not None):
            target_path.append('.'.join(frame.module.name_segments))

            if frame.module.entry_main and (frame.module.name_segments[-1] != '__main__'):
              target_path[-1] += ' (as __main__)'

          if frame.target is not None:
            ancestor_names = [ancestor.name for ancestor in frame.target.ancestors()]
            target_path += ancestor_names

            if ancestor_names:
              emphasize_last = True
          elif frame.target_name is not None:
            target_path.append(frame.target_name)
            emphasize_last = True

          if target_path:
            separator = f' {symbols.chevron_right} '
            target_path_lens = [len(segment) for segment in target_path]

            condense_left_index, condense_right_index = util.condense_seq(
              target_path_lens,
              ellipsis_width=len(symbols.ellipsis),
              priority_left=False,
              separator_width=len(separator),
              width=(most_available_width - frame_title_left_len),
            )

            if (condense_left_index < len(target_path)) and (condense_right_index >= len(target_path)):
              ancestors_ellipsis = symbols.ellipsis + separator if len(target_path) > 1 else ''
              wrapped_target_name = util.wrap_into_ellipsis(target_path[-1], ellipsis=symbols.ellipsis, width=(most_available_width - frame_title_left_len))

              frame_title_left += ancestors_ellipsis

              if emphasize_last:
                frame_title_left += symbols.underline

              frame_title_left += wrapped_target_name

              if emphasize_last:
                frame_title_left += symbols.underline_reset

              frame_title_left_len += len(ancestors_ellipsis) + len(wrapped_target_name)
            else:
              string, string_len = util.format_condensed_seq(
                [
                  (symbols.underline + name + symbols.underline_reset) if (name_index == len(target_path) - 1) and emphasize_last else name
                  for name_index, name in enumerate(target_path)
                ],
                target_path_lens,
                (condense_left_index, condense_right_index),
                ellipsis=symbols.ellipsis,
                ellipsis_width=len(symbols.ellipsis),
                separator=separator,
                separator_width=len(separator),
              )

              frame_title_left += string
              frame_title_left_len += string_len

          elif frame.target_is_module:
            string = 'module'
            frame_title_left += string
            frame_title_left_len += len(string)
          else:
            string = 'file'
            frame_title_left += string
            frame_title_left_len += len(string)

          frame_title_left += title_left_suffix


          # Frame right title

          if frame.area is not None:
            line_start_fmt = f':{frame.area.line_start}'
          else:
            line_start_fmt = ''

          frame_title_right_len = len(line_start_fmt)

          if frame.module.relative_path is not None:
            assert frame.module.path is not None

            condensed_path, condensed_path_len = util.condense_parts(
              frame.module.relative_path.parts,
              ellipsis=symbols.ellipsis,
              separator='/',
              width=(most_available_width - frame_title_right_len),
            )

            frame_title_right = symbols.link(
              condensed_path,
              frame.module.path.as_uri(),
              column_number=(frame.area.col_start if frame.area is not None else None),
              line_number=(frame.area.line_start if frame.area is not None else None),
            )

            frame_title_right_len += condensed_path_len
          elif frame.module.label is not None:
            string = util.wrap_into_ellipsis(frame.module.label, ellipsis=symbols.ellipsis, width=(most_available_width - frame_title_right_len))
            frame_title_right = string
            frame_title_right_len += len(string)
          else:
            string = '<unknown>'
            frame_title_right = string
            frame_title_right_len += len(string)

          frame_title_right += line_start_fmt


          # Frame title joining

          if frame_title_left_len + frame_title_right_len < available_width - 8:
            yield (
                frame_prefix
              + frame_indent
              + frame_title_color
              + frame_title_left
              + ' ' * (available_width - frame_title_left_len - frame_title_right_len)
              + frame_title_right
              + symbols.color_reset,

                len(frame_prefix)
              + len(frame_indent)
              + available_width,
            )

          else:
            yield (
                frame_prefix
              + frame_indent
              + frame_title_color
              + frame_title_left
              + symbols.color_reset,

                len(frame_prefix)
              + len(frame_indent)
              + frame_title_left_len,
            )

            yield (
                frame_prefix
              + frame_indent
              + ' ' * (available_width - frame_title_right_len)
              + frame_title_color
              + frame_title_right
              + symbols.color_reset,

                len(frame_prefix)
              + len(frame_indent)
              + available_width,
            )


          # Frame trace

          if (atom_index, agg_frame_index) in trace_indices:
            frame = agg_frame

            assert frame.area is not None
            assert frame.module.source is not None

            line_start = frame.area.line_start
            line_end = frame.area.line_end
            col_start = frame.area.col_start
            col_end = frame.area.col_end

            code_lines = frame.module.source.splitlines()

            match frame.area:
              case FrameAreaFull(line_start, line_end, col_start, col_end):
                pass
              case FrameAreaLines(line_start, line_end):
                col_start = util.lcount_whitespace(code_lines[line_start - 1])
                col_end = len(code_lines[line_end - 1]) - util.rcount_whitespace(code_lines[line_end - 1])
              case FrameAreaStartLineCol(line_start, col_start):
                line_end = line_start
                col_end = col_start + 1
              case FrameAreaStartLine(line_start):
                line_end = line_start
                col_start = 0
                col_start = util.lcount_whitespace(code_lines[line_start - 1])
                col_end = len(code_lines[line_end - 1]) - util.rcount_whitespace(code_lines[line_end - 1])
              case _:
                raise UnreachableError


            # Compute target line range

            # Ensure there are no more than max_total_lines target lines
            if line_end - line_start + 1 > options.max_target_lines:
              # The "more lines" message always mentions at least 2 lines
              line_end_cut = line_start + options.max_target_lines - 2
            else:
              line_end_cut = line_end


            # Compute context line range

            context_line_start = max(line_start - options.max_context_lines_before, 1)
            context_line_end = min(line_end + options.max_context_lines_after, len(code_lines))

            while (context_line_start < line_start) and (not (context_line := code_lines[context_line_start - 1]) or context_line.isspace()):
              context_line_start += 1

            # This must be done beforehand in order to calculate the maximum line width
            while (context_line_end > line_end) and (not (context_line := code_lines[context_line_end - 1]) or context_line.isspace()):
              context_line_end -= 1

            final_line = line_end_cut if context_line_end == line_end else context_line_end


            # Compute line parameters

            # Also includes cut target lines
            displayed_lines = code_lines[(context_line_start - 1):context_line_end]
            lines_common_indent = util.get_common_indentation(displayed_lines) if options.remove_common_indentation else 0


            trace_prefix = frame_prefix + frame_indent + generic_indent_str
            trace_width = available_width - len(generic_indent_str)

            line_number_width = util.get_integer_width(final_line)
            line_number_sep = ' '
            code_width = trace_width - line_number_width - len(line_number_sep)


            # Display context before target

            for rel_line_index, line in enumerate(code_lines[(context_line_start - 1):(line_start - 1)]):
              line_number = context_line_start + rel_line_index
              line_truncated = util.wrap_into_ellipsis(line[lines_common_indent:], ellipsis=symbols.ellipsis, width=code_width)

              yield (
                  trace_prefix
                + symbols.color_bright_black
                + f'{line_number: >{line_number_width}}'
                + line_number_sep
                + line_truncated
                + symbols.color_reset,

                  len(trace_prefix)
                + line_number_width
                + len(line_number_sep)
                + len(line_truncated),
              )


            # Display target

            target_lines = code_lines[(line_start - 1):line_end_cut]

            for rel_line_index, line in enumerate(target_lines):
              line_pretruncated = line[lines_common_indent:]

              line_number = line_start + rel_line_index
              line_indent = util.lcount_whitespace(line_pretruncated)
              line_indent_skippable = line_indent if options.skip_indentation_highlight else 0

              if line_number == line_start:
                anchor_start = col_start

                if line_start == line_end:
                  anchor_end = col_end
                else:
                  anchor_end = len(line)
              elif line_number == line_end:
                anchor_start = line_indent_skippable
                anchor_end = col_end
              else:
                anchor_start = line_indent_skippable
                anchor_end = len(line)

              anchor_start_sub = max(anchor_start - lines_common_indent, 0)
              anchor_end_sub = max(anchor_end - lines_common_indent, 0)

              line_truncated = line_pretruncated[line_indent:]

              match profile:
                case 'default':
                  highlight_color = symbols.color_red
                case 'warning':
                  highlight_color = symbols.color_orange
                case _:
                  raise UnreachableError

              for wrapped_line_index, (wrapped_line_start, wrapped_line_end) in enumerate(util.wrap_into_paragraph_indices(line_truncated, width=(code_width - line_indent))):
                wrapped_line_first = wrapped_line_index == 0

                yield (
                    trace_prefix
                  + (f'{line_number: >{line_number_width}}' if wrapped_line_first else ' ' * line_number_width)
                  + line_number_sep
                  + line_pretruncated[:line_indent]
                  + line_truncated[wrapped_line_start:wrapped_line_end],

                    len(trace_prefix)
                  + line_number_width
                  + len(line_number_sep)
                  + line_indent
                  + (wrapped_line_end - wrapped_line_start),
                )

                line_indent_skipped = line_indent_skippable if wrapped_line_first else line_indent

                if (anchor_start_sub < wrapped_line_end + line_indent) and (anchor_end_sub >= wrapped_line_start + line_indent_skipped):
                  highlight_start = max(anchor_start_sub, wrapped_line_start + line_indent_skipped) - wrapped_line_start
                  highlight_end = min(anchor_end_sub, wrapped_line_end + line_indent) - wrapped_line_start

                  yield (
                      trace_prefix
                    + ' ' * line_number_width
                    + line_number_sep
                    + ' ' * highlight_start
                    + highlight_color
                    + '^' * (highlight_end - highlight_start)
                    + symbols.color_reset,

                      len(trace_prefix)
                    + line_number_width
                    + len(line_number_sep)
                    + highlight_end,
                  )

                  newline_required = not skip_newline_on_highlights_at_trace_ends
                else:
                  newline_required = True

            if line_end_cut != line_end:
              cut_message = f"{frame_indent}{generic_indent_str}{' ' * (line_number_width + 1)}[{line_end - line_end_cut} more lines]"
              yield cut_message, len(cut_message)

              newline_required = True


            # Display context after target

            for rel_line_index, line in enumerate(code_lines[line_end:context_line_end]):
              line_number = line_end + rel_line_index + 1
              line_truncated = util.wrap_into_ellipsis(line[lines_common_indent:], ellipsis=symbols.ellipsis, width=code_width)

              yield (
                  trace_prefix
                + symbols.color_bright_black
                + f'{line_number: >{line_number_width}}'
                + line_number_sep
                + line_truncated
                + symbols.color_reset,

                  len(trace_prefix)
                + line_number_width
                + len(line_number_sep)
                + len(line_truncated),
              )

              newline_required = True

        case LibraryFrameAggregate(frames=agg_frames, package_name=name):
          assert atom.repeat_count == 1

          def map_frame(frame: FrameItem):
            assert frame.module.name_segments is not None
            return frame.module.name_segments

          module_segments_list = [map_frame(frame) for frame in agg_frames]

          agg_name_segments = util.find_common_ancestors(module_segments_list)
          module_unique = all(len(name_segments) == len(agg_name_segments) for name_segments in module_segments_list)

          if len(agg_frames) > 1:
            frame_title_suffix = f' [{len(agg_frames)} frames]'
          else:
            frame_title_suffix = ''

          frame_title_len = len(frame_title_suffix)

          string = 'in module' + ('s' if not module_unique else '') + ' '
          frame_title = string
          frame_title_len += len(string)

          string = util.wrap_into_ellipsis(
            '.'.join(agg_name_segments) + ('.*' if not module_unique else ''),
            ellipsis=symbols.ellipsis,
            width=(most_available_width - frame_title_len),
          )

          if string.endswith('.'):
            string = string[:-1]

          frame_title += string
          frame_title += frame_title_suffix
          frame_title_len += len(string)

          yield (
              frame_prefix
            + frame_indent
            + symbols.color_bright_black
            + frame_title
            + symbols.color_reset,

              len(frame_prefix)
            + len(frame_indent)
            + frame_title_len,
          )

          newline_required = False

        case _:
          raise UnreachableError

    if repeat_box_indent is not None:
      repeat_box_header = repeat_box_indent + symbols.box_up_right + (symbols.box_horizontal * 3)
      yield repeat_box_header, len(repeat_box_header)

      newline_required = True

  if newline_required:
    yield '', 0
