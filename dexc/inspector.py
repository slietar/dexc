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
from typing import TYPE_CHECKING, Literal, Optional, TypeAlias

from .vendor import get_ipython

if TYPE_CHECKING:
  from .extract import FrameItem


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
  entry_main: Optional[bool]
  instance: Optional[ModuleType]
  kind: ModuleKind
  label: Optional[str]
  name_segments: Optional[tuple[str, ...]]
  path: Optional[Path]
  source: Optional[str] = field(repr=False)
  relative_path: Optional[Path]


@dataclass
class ModuleInspector:
  cache: dict[Path, ModuleInfo] = field(default_factory=dict)

  @functools.cached_property
  def distribution_map(self):
    return importlib.metadata.packages_distributions()

  def inspect(
    self,
    filename: str,
    frame: Optional[FrameType] = None,
    *,
    partial_source: Optional[PartialSource] = None,
    previous_frame: 'Optional[FrameItem]' = None,
  ):
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


    # Get name segments

    if instance is not None:
      name_segments = tuple(instance.__name__.split('.'))
      entry_main = name_segments == ('__main__',)

      if entry_main:
        if instance.__spec__ is not None:
          name_segments = tuple(instance.__spec__.name.split('.'))
        else:
          name_segments = None
    else:
      entry_main = None
      name_segments = None


    # Get relative path

    if path is not None:
      cwd = Path.cwd()
      roots = [*(p for path in sys.path if path and ((p := Path(path)) != cwd) and not p.suffix), cwd]

      for root in roots:
        # print("Test", path, root, repr(root.suffix))
        try:
          potential_relative_path = path.relative_to(root)
        except ValueError:
          pass
        else:
          potential_name_segments = (
            tuple(potential_relative_path.parent.parts) +
            ((path.stem,) if path.name != '__init__.py' else ())
          )

          if name_segments is not None:
            if name_segments != potential_name_segments:
              continue
          else:
            name_segments = potential_name_segments

          in_cwd = root == cwd
          relative_path = potential_relative_path
          break
      else:
        in_cwd = False
        relative_path = None
    else:
      in_cwd = False
      relative_path = None


    # if (name_segments is not None) and (path is not None) and (name_segments != ('__main__',)):
    #   path_parts = list(name_segments)

    #   if path.name == '__init__.py':
    #     path_parts.append('__init__.py')
    #   else:
    #     path_parts[-1] += '.py'

    #   relative_path: Optional[Path] = functools.reduce(operator.truediv, path_parts, Path('.'))
    # else:
    #   relative_path = None

    # if path is not None:
    #   relative_path, in_syspath = get_relative_path(path, name_segments)
    # else:
    #   in_syspath = False
    #   relative_path = None


    # Improve module kind

    distribution = None
    editable = False
    module_kind: ModuleKind

    if name_segments is None:
      module_kind = 'user'
    else:
      if name_segments in (
        ('importlib', '_bootstrap'),
        ('importlib', '_bootstrap_external'),
        ('runpy',),
      ):
        module_kind = 'internal'
      elif name_segments[0] in sys.stdlib_module_names:
        module_kind = 'std'
      else:
        distribution_names = self.distribution_map.get(name_segments[0])

        if (distribution_names is None) or in_cwd:
          module_kind = 'user'
        else:
          module_kind = 'lib'

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
      entry_main=entry_main,
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


def resolve_import(importer_name_segments: tuple[str, ...], node: ast.Import | ast.ImportFrom, *, init_or_main: bool = False):
  if len(node.names) > 1:
    return None

  match node:
    case ast.Import():
      return tuple(node.names[0].name.split('.'))

    case ast.ImportFrom():
      truncate_level = node.level - (1 if init_or_main else 0)

      return (
        importer_name_segments[:(-truncate_level if truncate_level > 0 else None)]
        + (tuple(node.module.split('.')) if node.module else ())
        + tuple(node.names[0].name.split('.'))
      )
