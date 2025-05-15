import ast
import functools
import importlib.metadata
import inspect
import linecache
import sys
from dataclasses import dataclass, field
from importlib.metadata import Distribution
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
  distribution: Optional[Distribution]
  editable: bool
  instance: Optional[ModuleType]
  kind: ModuleKind
  label: Optional[str]
  name_segments: Optional[tuple[str, ...]]
  path: Optional[Path]
  source: Optional[str] = field(repr=False)
  relative_path: Optional[Path]


@dataclass # (slots=True)
class ModuleInspector:
  cache: dict[Path, ModuleInfo] = field(default_factory=dict)

  @functools.cached_property
  def distribution_map(self):
    return importlib.metadata.packages_distributions()

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


    # Get relative path

    if path is not None:
      relative_path, in_syspath = get_relative_path(path)
    else:
      in_syspath = False
      relative_path = None


    # Get name segments

    if instance is not None:
      name_segments = tuple(instance.__name__.split('.'))
    elif relative_path is not None:
      name_segments = relative_path.with_suffix('').parts

      if name_segments[-1] == '__init__':
        name_segments = name_segments[:-1]
    else:
      name_segments = None


    # Improve module kind

    distribution = None
    editable = False
    module_kind: ModuleKind

    if name_segments is None:
      module_kind = 'user'
    else:
      if name_segments == ('__main__',):
        module_kind = 'user'
      elif name_segments in (
        ('importlib', '_bootstrap'),
        ('importlib', '_bootstrap_external'),
        ('runpy',),
      ):
        module_kind = 'internal'
      elif name_segments[0] in sys.stdlib_module_names:
        module_kind = 'std'
      else:
        distribution_names = self.distribution_map.get(name_segments[0])

        if distribution_names is None:
          module_kind = 'user'
        else:
          module_kind = 'user' # 'lib' if in_syspath else 'user'

          for distribution_name in distribution_names:
            distribution = importlib.metadata.distribution(distribution_name)
            direct_url = distribution.read_text('direct_url.json')

            if direct_url is not None:
              import json

              try:
                direct_url = json.loads(direct_url)
              except json.JSONDecodeError:
                pass
              else:
                editable = direct_url.get('dir_info', {}).get('editable', False)

                if editable:
                  module_kind = 'user'
                  break


    # Create environment

    env = ModuleInfo(
      ast=tree,
      distribution=distribution,
      editable=editable,
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
