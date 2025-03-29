import ast
import math
import os
import sys
from dataclasses import dataclass, field
from pprint import pprint
from typing import IO, Any, Container, Iterable, Literal, Optional, Sequence

from .compression import Atom
from .compression.greedy import compress
from .extract import ExceptionChain, FrameItem, ModuleInfo
from .options import Options
from .util import UnreachableError, find_common_ancestors, reversed_if, split_paragraph
from .vendor import get_ipython


def get_integer_width(x: int, /):
  return max(math.ceil(math.log10(x + 1)), 1)

def get_line_indentation(line: str, /):
  return len(line) - len(line.lstrip())

def get_common_indentation(lines: list[str], /):
  return min(len(line) - len(stripped_line) for line in lines if (stripped_line := line.lstrip()))


@dataclass(slots=True)
class Symbols:
  color_bright_black: str
  color_italic: str
  color_orange: str
  color_red: str
  color_reset: str
  color_underline: str
  color_yellow: str

  box_down_right: str
  box_horizontal: str
  box_up_right: str
  box_vertical_right: str
  box_vertical: str

  def __init__(self, *, ascii_only: bool, colorize: bool):
    if ascii_only:
      self.box_down_right = '+'
      self.box_horizontal = '-'
      self.box_up_right = '+'
      self.box_vertical = '|'
      self.box_vertical_right = '+'
    else:
      self.box_down_right = '\u250c'
      self.box_horizontal = '─'
      self.box_up_right = '\u2514'
      self.box_vertical = '\u2502'
      self.box_vertical_right = '\u251c'

    if colorize:
      self.color_bright_black = '\033[90m'
      self.color_italic = '\033[3m'
      self.color_orange = '\033[38;5;208m'
      self.color_red = '\033[31m'
      self.color_reset = '\033[0m'
      self.color_underline = '\033[4m'
      self.color_yellow = '\033[33m'
    else:
      self.color_bright_black = ''
      self.color_italic = ''
      self.color_orange = ''
      self.color_red = ''
      self.color_reset = ''
      self.color_underline = ''
      self.color_yellow = ''

  @classmethod
  def from_file(cls, file: IO[str], options: Options):
    colorize = options.colorize or (
      (options.colorize is None) and
      (not os.environ.get('NO_COLOR')) and
      (file.isatty() or (
        (file == sys.stderr) and
        (get_ipython() is not None))
      )
    )

    return cls(
      ascii_only=options.ascii_only,
      colorize=colorize,
    )


@dataclass(slots=True)
class LibraryFrameAggregate:
  package_name: str
  frames: list[FrameItem] = field(default_factory=list)

  def __hash__(self):
    return id(self)

type AggregatedFrame = FrameItem | LibraryFrameAggregate

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


type RenderProfile = Literal['default', 'warning']

def render(
  chain: ExceptionChain,
  file: IO[str],
  options: Options,
  prefix: str = '',
  profile: RenderProfile = 'default',
  _symbols: Optional[Symbols] = None,
):
  file.write(prefix)

  render_item(
    chain,
    file,
    options,
    floating=False,
    indent='',
    prefix=prefix,
    profile=profile,
    symbols=(_symbols if _symbols is not None else Symbols.from_file(file, options)),
  )


def render_item(
  chain: ExceptionChain,
  file: IO[str],
  options: Options,
  *,
  floating: bool,
  indent: str,
  prefix: str,
  profile: RenderProfile,
  symbols: Symbols,
  width: int = 80, # Excluding indent and prefix
):
  newline_required = False

  for item, relation in (
    zip(chain.items[::-1], [None, *chain.relations[::-1]])
    if options.chain_origin_on_top
    else zip(chain.items, [None, *chain.relations])
  ):
    if newline_required:
      file.write(f'{prefix}\n')
      newline_required = False

    # Relation

    if relation is not None:
      file.write(f'{prefix}\n{prefix}{symbols.color_italic}[')

      match relation:
        case 'cause':
          file.write('Causing' if options.chain_origin_on_top else 'Caused by')
        case 'context':
          file.write('Raising while handling' if options.chain_origin_on_top else 'Raised while handling')

      file.write(f']{symbols.color_reset}\n{prefix}\n{prefix}')


    # Description

    current_prefix, current_indent = (prefix + indent + symbols.box_vertical, ' ') if item.children else (prefix, indent)
    current_width = (width - 1) if item.children else width

    desc = str(item.instance)
    desc_indent = '  ' if not item.children else ''
    desc_lines = desc.splitlines()
    desc_width = current_width - len(desc_indent)

    exc_type_name = type(item.instance).__name__
    file.write(exc_type_name)

    if desc:
      if (len(desc_lines) == 1) and (len(desc) <= current_width - len(exc_type_name) - len(': ')):
        file.write(f': {desc}\n')
      else:
        file.write('\n')

        for desc_line in split_paragraph(desc_lines, width=desc_width):
          file.write(current_prefix + current_indent + desc_indent + desc_line + '\n')

        newline_required = True
    else:
      file.write('\n')


    # Notes

    notes = getattr(item.instance, '__notes__', [])
    note_indent = '  ' if not floating else ''

    for note in notes:
      note_lines = note.splitlines()

      if newline_required:
        file.write(f'{current_prefix}\n')

      file.write(f'{current_prefix + current_indent + note_indent}{symbols.color_underline}note{symbols.color_reset}')

      if len(note_lines) > 1:
        file.write('\n')

        for note_line in note_lines:
          file.write(current_prefix + current_indent + note_indent + '  ' + note_line + '\n')

        newline_required = True
      else:
        file.write(f' {note}\n')
        newline_required = False

    if notes:
      newline_required = True


    # Frames

    if item.frames:
      if newline_required:
        file.write(f'{current_prefix}\n')

      # Reversing here so we don't have to reverse every atom later on
      if options.inner_frame_on_top:
        frames = item.frames
      else:
        frames = reversed(item.frames)

      aggregated_frames = aggregate_frames(frames, options)
      atoms = compress(aggregated_frames, backwards=(not options.compression_first_on_top), key=hash)
      # pprint(aggregated_frames)

      trace_indices = set[tuple[int, int]]()

      for atom_inner_index, (atom_display_index, atom) in enumerate(reversed_if(list(enumerate(atoms)), not options.inner_frame_on_top)):
        for agg_frame_index, agg_frame in reversed_if(list(enumerate(atom.realization[:len(atom.keys)])), not options.inner_frame_on_top):
          if isinstance(agg_frame, FrameItem) and agg_frame.important and agg_frame.traceable and (len(trace_indices) < options.max_traces):
            trace_indices.add((atom_display_index, agg_frame_index))

      newline_required = render_frames(
        atoms,
        # item.frames,
        # [],
        file,
        options,
        prefix=f'{current_prefix + current_indent}{'  ' if not floating else ''}',
        profile=profile,
        symbols=symbols,
        trace_indices=trace_indices,
      )


    # Children

    for child_index, child in enumerate(item.children):
      if newline_required:
        file.write(f'{current_prefix}\n')

      is_child_last = child_index == len(item.children) - 1
      child_prefix, child_indent = (prefix, indent + '    ') if is_child_last else (prefix + indent + symbols.box_vertical, '   ')

      file.write(f'{prefix + indent}{symbols.box_up_right if is_child_last else symbols.box_vertical_right}{symbols.box_horizontal * 2} ')

      newline_required = render_item(
        child,
        file,
        options,
        floating=True,
        indent=child_indent,
        prefix=child_prefix,
        profile=profile,
        symbols=symbols,
      )

  return newline_required


def render_frames(
  atoms: Sequence[Atom[AggregatedFrame, Any]],
  file: IO[str],
  options: Options,
  *,
  prefix: str,
  profile: RenderProfile,
  symbols: Symbols,
  trace_indices: Container[tuple[int, int]],
):
  # Additional options
  indent = '  '
  inset_repeat_box = True
  skip_newline_on_highlights_at_trace_ends = True

  # Whether a newline is required before the next frame
  newline_required = False

  for atom_index, atom in enumerate(atoms):
    # atom_correct_index = atom_index if options.inner_frame_on_top else len(atoms) - atom_index - 1
    repeat_box = (atom.repeat_count > 1) and (len(atom.keys) > 1)

    if repeat_box and (atom_index > 0):
      newline_required = True

    if newline_required:
      file.write(prefix + '\n')
      newline_required = False

    if repeat_box:
      if inset_repeat_box and (prefix[-2:] == indent):
        repeat_box_prefix = prefix[:-2]
      else:
        repeat_box_prefix = prefix

      frame_prefix = repeat_box_prefix + symbols.box_vertical + ' '
      file.write(f'{repeat_box_prefix}{symbols.box_down_right}{symbols.box_horizontal * 2} Repeated {atom.repeat_count} times {symbols.box_horizontal * 2}\n')
    else:
      frame_prefix = prefix
      repeat_box_prefix = None

    for agg_frame_index, agg_frame in enumerate(atom.realization[:len(atom.keys)]):
      if newline_required:
        file.write(frame_prefix + '\n')

      file.write(frame_prefix)

      match agg_frame:
        case FrameItem():
          frame = agg_frame

          color = symbols.color_bright_black if not frame.important else ''
          file.write(color)

          if frame.target is not None:
            target_name = None

            for node in [frame.target.node, *frame.target.parents[::-1]]:
              match node:
                case ast.AsyncFunctionDef(name=name) | ast.FunctionDef(name=name):
                  file.write('at function ')
                  target_name = name
                  break
                case ast.ClassDef(name=name):
                  file.write('at class ')
                  target_name = name
                  break
                case ast.Module():
                  file.write(f'at module ')
                  break

            if target_name is not None:
              file.write(f'{symbols.color_underline}{target_name}{symbols.color_reset}{color} ')

          if frame.module.name_segments is not None:
            file.write(f'in {'.'.join(frame.module.name_segments)}')
          elif frame.module.label is not None:
            file.write(f'in {frame.module.label}')
          else:
            file.write('in unknown module')

          if frame.module.relative_path is not None:
            file.write(' (')

            if frame.module.kind == 'user':
              file.write('./')

            file.write(f'{frame.module.relative_path}')

            if frame.area.line_start is not None:
              file.write(f':{frame.area.line_start}')

            file.write(')')

          if frame.reraise:
            file.write(' [re-raise]')

          if (atom.repeat_count > 1) and (len(atom.keys) == 1):
            file.write(f' [repeated {atom.repeat_count} times]')

          file.write(f'{symbols.color_reset}\n')

          if (atom_index, agg_frame_index) in trace_indices:
            frame = agg_frame

            line_start = frame.area.line_start
            line_end = frame.area.line_end
            col_start = frame.area.col_start
            col_end = frame.area.col_end

            assert line_start is not None
            assert line_end is not None
            assert col_start is not None
            assert col_end is not None
            assert frame.module.source is not None

            code_lines = frame.module.source.splitlines()


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


            # Compute line parameters

            # Also includes cut target lines
            displayed_lines = code_lines[(context_line_start - 1):context_line_end]
            common_indentation = get_common_indentation(displayed_lines) if options.remove_common_indentation else 0

            line_number_width = get_integer_width(context_line_end)


            # Display context before target

            trace = ''

            for rel_line_index, line in enumerate(code_lines[(context_line_start - 1):(line_start - 1)]):
              line_number = context_line_start + rel_line_index
              trace += f'{frame_prefix}{symbols.color_bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{symbols.color_reset}\n'


            # Display target

            target_lines = code_lines[(line_start - 1):line_end_cut]

            for rel_line_index, line in enumerate(target_lines):
              line_number = line_start + rel_line_index
              line_indent = get_line_indentation(line) if options.skip_indentation_highlight else 0

              if line_number == line_start:
                anchor_start = col_start

                if line_start == line_end:
                  anchor_end = col_end
                else:
                  anchor_end = len(line)
              elif line_number == line_end:
                anchor_start = line_indent
                anchor_end = col_end
              else:
                anchor_start = line_indent
                anchor_end = len(line)

              anchor_start_sub = max(anchor_start - common_indentation, 0)
              anchor_end_sub = max(anchor_end - common_indentation, 0)

              trace += f'{frame_prefix}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}\n'
              trace += frame_prefix + indent + ' ' * (line_number_width + 1 + anchor_start_sub)

              match profile:
                case 'default':
                  trace += symbols.color_red
                case 'warning':
                  trace += symbols.color_orange
                case _:
                  raise UnreachableError

              trace += '^' * (anchor_end_sub - anchor_start_sub)
              trace += symbols.color_reset + '\n'

            if line_end_cut != line_end:
              trace += f'{frame_prefix}{indent}{' ' * (line_number_width + 1)}[{line_end - line_end_cut} more lines]\n'


            # Display context after target

            for rel_line_index, line in enumerate(code_lines[line_end:context_line_end]):
              line_number = line_end + rel_line_index + 1
              trace += f'{frame_prefix}{symbols.color_bright_black}{indent}{line_number: >{line_number_width}} {line[common_indentation:]}{symbols.color_reset}\n'

            file.write(trace)

            # The line of ^^^^ can be considered a newline
            newline_required = (line_end != context_line_end) or (line_end_cut != line_end) or (not skip_newline_on_highlights_at_trace_ends)

        case LibraryFrameAggregate(frames=agg_frames, package_name=name):
          assert atom.repeat_count == 1

          def map_frame(frame: FrameItem):
            assert frame.module.name_segments is not None
            return frame.module.name_segments

          module_segments_list = [map_frame(frame) for frame in agg_frames]

          agg_name_segments = find_common_ancestors(module_segments_list)
          module_unique = all(len(name_segments) == len(agg_name_segments) for name_segments in module_segments_list)

          file.write(f'{symbols.color_bright_black}in module{'s' if not module_unique else ''} {'.'.join(agg_name_segments)}{'.*' if not module_unique else ''}')

          if len(agg_frames) > 1:
            file.write(f' [{len(agg_frames)} frames]')

          file.write(f'{symbols.color_reset}\n')

          newline_required = False

        case _:
          raise UnreachableError

    if repeat_box_prefix is not None:
      file.write(f'{repeat_box_prefix}{symbols.box_up_right}{symbols.box_horizontal * 3}\n')
      newline_required = True

  return newline_required
