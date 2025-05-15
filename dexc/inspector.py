import ast
import inspect
import linecache
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType, ModuleType
from typing import Literal, Optional, TypeAlias

from .util import get_relative_path
from .vendor import get_ipython


@dataclass(slots=True)
class PartialSource:
  contents: str
  start_line: int


ModuleKind: TypeAlias = Literal['internal', 'std', 'lib', 'user']

@dataclass(eq=True, frozen=True, slots=True)
class ModuleInfo:
  ast: Optional[ast.Module]
  instance: Optional[ModuleType]
  kind: ModuleKind
  label: Optional[str]
  name_segments: Optional[tuple[str, ...]]
  path: Optional[Path]
  source: Optional[str] = field(repr=False)
  relative_path: Optional[Path]


@dataclass(slots=True)
class ModuleInspector:
  cache: dict[Path, ModuleInfo] = field(default_factory=dict)

  def inspect(self, filename: str, frame: Optional[FrameType] = None, partial_source: Optional[PartialSource] = None):
    instance = inspect.getmodule(frame.f_code) if frame is not None else None
    filename_special = filename.startswith('<') and filename.endswith('>')


    # Find instance in some rare cases

    if (frame is not None) and (instance is None) and filename.startswith('<frozen ') and filename.endswith('>'):
      name = frame.f_globals.get('__name__')

      if name is not None:
        instance = sys.modules.get(name)


    # Find path using instance or code

    path_raw = (
      (inspect.getabsfile(instance) if instance is not None else None) or
      (inspect.getabsfile(frame.f_code) if (frame is not None) and not filename_special else None)
    )

    if path_raw is not None:
      path = Path(path_raw)
    else:
      path = None


    # Find path using filename

    if (path is None) and not filename_special:
      path = Path(filename)


    # Lookup cache

    if (path is not None) and (path in self.cache):
      return self.cache[path]


    # Find source

    if instance is not None:
      try:
        source = inspect.getsource(instance)
      except OSError:
        source = None
    else:
      source = None

    if (source is None) and (path is not None):
      source_lines = linecache.getlines(str(path))

      if source_lines:
        source = ''.join(source_lines)
      else:
        source = None


    # Parse source

    if source is not None:
      try:
        tree = ast.parse(source)
      except SyntaxError:
        tree = None
    else:
      tree = None


    # Try a partial source

    if (source is None) and (partial_source is not None):
      source = '\n' * (partial_source.start_line - 1) + partial_source.contents

    # Find label

    ipython = get_ipython()

    if (path is not None) and (ipython is not None):
      ipython_label = ipython.compile.format_code_name(str(path))

      if ipython_label is not None:
        label = ' '.join(ipython_label)
      else:
        label = None
    elif filename_special:
      label = filename
    else:
      label = None


    # Get relative path and module kind

    module_kind: ModuleKind

    if path is not None:
      relative_path, in_syspath = get_relative_path(path)
      module_kind = 'lib' if in_syspath else 'user'
    else:
      relative_path = None
      module_kind = 'user'

    if instance is not None:
      name_segments = tuple(instance.__name__.split('.'))
    elif relative_path is not None:
      name_segments = relative_path.with_suffix('').parts

      if name_segments[-1] == '__init__':
        name_segments = name_segments[:-1]
    else:
      name_segments = None


    # Mark standard library and internal modules

    if name_segments is not None:
      if name_segments in (
        ('importlib', '_bootstrap'),
        ('importlib', '_bootstrap_external'),
        ('runpy',),
      ):
        module_kind = 'internal'
      elif name_segments[0] in sys.stdlib_module_names:
        module_kind = 'std'


    # Create environment

    env = ModuleInfo(
      ast=tree,
      instance=instance,
      kind=module_kind,
      label=label,
      name_segments=name_segments,
      path=path,
      source=source,
      relative_path=relative_path,
    )

    if (path is not None):
      self.cache[path] = env

    return env
