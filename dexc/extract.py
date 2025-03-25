import ast
import functools
import inspect
import itertools
import sys
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pprint
from types import ModuleType, TracebackType
from typing import Literal, Optional

from .util import get_relative_path, try_read_text


type AstNode = ast.Module | ast.expr | ast.stmt

@dataclass(frozen=True, slots=True)
class AstTarget:
  node: AstNode
  parents: list[AstNode] = field(hash=False)


type ModuleKind = Literal['internal', 'std', 'lib', 'user']

@dataclass(frozen=True, slots=True)
class ModuleEnvironment:
  ast: Optional[ast.Module]
  instance: Optional[ModuleType]
  kind: ModuleKind
  name: Optional[str]
  path: Optional[Path]
  source: Optional[str] = field(repr=False)
  relative_path: Optional[Path]

@dataclass(frozen=True, slots=True)
class LabeledEnvironment:
  label: str

type Environment = LabeledEnvironment | ModuleEnvironment


@dataclass(frozen=True, slots=True)
class FrameArea:
  line_start: Optional[int]
  line_end: Optional[int]
  col_start: Optional[int]
  col_end: Optional[int]

@dataclass(eq=True, frozen=True, slots=True)
class FrameItem:
  area: FrameArea
  env: Environment
  target: Optional[AstTarget]
  reraise: bool


type ExceptionChainRelation = Literal['cause', 'context']

@dataclass(slots=True)
class ExceptionItem:
  children: 'list[ExceptionChain]'
  frames: list[FrameItem]
  instance: BaseException

@dataclass(slots=True)
class ExceptionChain:
  items: list[ExceptionItem]
  relations: list[ExceptionChainRelation]


def extract(start_exc: BaseException, /):
  return extract_exc_chain(start_exc)

def extract_exc_chain(start_exc: BaseException, /):
  current_exc = start_exc

  excs = list[BaseException]()
  excs.append(current_exc)

  relations = list[ExceptionChainRelation]()

  while True:
    if current_exc.__cause__:
      current_exc = current_exc.__cause__
      excs.append(current_exc)
      relations.append('cause')
    elif current_exc.__context__:
      current_exc = current_exc.__context__
      excs.append(current_exc)
      relations.append('context')
    else:
      break

  def map_exc(exc: BaseException):
    return ExceptionItem(
      children=([extract_exc_chain(exc) for exc in exc.exceptions] if isinstance(exc, BaseExceptionGroup) else []),
      frames=extract_exc_frames(exc),
      instance=exc,
    )

  return ExceptionChain([map_exc(exc) for exc in excs], relations=relations)



def extract_exc_frames(exc: BaseException, /):
  current_tb = exc.__traceback__
  tbs = list[TracebackType]()

  while current_tb:
    tbs.append(current_tb)
    current_tb = current_tb.tb_next

  # Detect syntax error

  frames = list[FrameItem]()
  is_syntax_error = False # isinstance(exc, SyntaxError)

  # if is_syntax_error:
  #   file.write(format_frame(
  #     escape=escape,
  #     frame_index=0,
  #     func_name=Path(exc.filename).name,
  #     prefix=prefix,
  #     raw_path=exc.filename,
  #     positions=(
  #       exc.lineno,
  #       exc.end_lineno,
  #       (exc.offset - 1) if exc.offset is not None else None,
  #       (
  #         (exc.end_offset - 1) if exc.end_offset > 0 else exc.offset
  #       ) if exc.end_offset is not None else None
  #     ),
  #     options=options
  #   ))


  # Extract frames

  for tb_index, tb in enumerate(reversed(tbs)):
    frame = tb.tb_frame
    frame_code = frame.f_code

    positions = next(
      itertools.islice(frame_code.co_positions(), tb.tb_lasti // 2, None)
    ) if tb.tb_lasti >= 0 else None

    area = FrameArea(
      positions[0] if positions is not None else None,
      positions[1] if positions is not None else None,
      positions[2] if positions is not None else None,
      positions[3] if positions is not None else None,
    )


    # Scenarios
    #
    #   1. Classic frame
    #   2. Internal frame e.g. <frozen importlib._bootstrap>
    #     - codeobj.co_filename is '<frozen ...>'
    #     - __name__ is not set
    #     - inspect.getmodule() is None
    #     - inspect.getsource() is available
    #   3. Compile + eval/exec
    #     - codeobj.co_filename is '<string>' or something similar
    #     - __name__ may correspond to wrong module
    #     - inspect.getmodule() is None
    #     - inspect.getsource() raises an OSError
    #   4. File is deleted before exception is handled, module fails to load (i.e. exception raised when loading module)
    #     - codeobj.co_filename is correct but points to missing file
    #     - __name__ is present but module is missing from sys.modules
    #     - inspect.getmodule() is None
    #     - inspect.getsource() raises an OSError
    #   5. File is deleted before exception is handled, module is loaded
    #     - codeobj.co_filename is correct but points to missing file
    #     - __name__ is present and points to module
    #     - inspect.getmodule() is correct
    #     - inspect.getsource() raises an OSError

    # print('>>', frame_code.co_qualname)
    # print(inspect.getmodule(frame_code))

    # try:
    #   inspect.getsource(frame_code)
    # except OSError:
    #   print('source not ok')
    # else:
    #   print('source ok')

    # print(frame.f_globals.get('__name__'))
    # print(sys.modules.get(frame.f_globals.get('__name__')))
    # print(sys.modules)


    module_instance = inspect.getmodule(frame_code)
    module_label = frame_code.co_filename

    if module_instance is None:
      if module_label.startswith('<frozen ') and module_label.endswith('>'):
        module_name = frame.f_globals.get('__name__')

        if module_name is not None:
          module_instance = sys.modules.get(module_name)

    if module_instance is not None:
      env = get_env_from_module_instance(module_instance)
    else:
      module_source_path = inspect.getsourcefile(frame_code)

      if module_source_path is not None:
        env = get_env_from_module_path(Path(module_source_path))
      else:
        env = LabeledEnvironment(label=module_label)

    # env = LabeledEnvironment(label=module_label)

    if isinstance(env, ModuleEnvironment) and (env.ast is not None) and (positions is not None):
      target = identify_node(env.ast, area)
    else:
      target = None

    frame = FrameItem(
      area=area,
      env=env,
      target=target,
      reraise=((tb_index > 0) and (target is not None) and isinstance(target.node, ast.Raise)),
    )

    frames.append(frame)

  return frames


@functools.cache
def get_env_from_module_instance(instance: ModuleType, /):
  return get_env_from_module(
    instance=instance,
    path=Path(inspect.getfile(instance)),
  )

@functools.cache
def get_env_from_module_path(path: Path, /):
  return get_env_from_module(
    instance=None,
    path=path,
  )

def get_env_from_module(
  instance: Optional[ModuleType],
  path: Path,
):
  # Get source

  if instance is not None:
    try:
      source = inspect.getsource(instance)
    except OSError:
      source = None
  else:
    source = None

  if source is None:
    source = try_read_text(path)

  # Get tree

  if source is not None:
    tree = ast.parse(source)
  else:
    tree = None

  # Get relative path and name

  relative_path, in_syspath = get_relative_path(path)

  if instance is not None:
    name = instance.__name__
  elif relative_path is not None:
    name = relative_path.with_suffix('').as_posix().replace('/', '.')
  else:
    name = None


  kind: ModuleKind = 'user' if not in_syspath else 'lib'

  if (name is not None) and (name.split('.', maxsplit=1)[0] in sys.builtin_module_names):
    kind = 'std'

  return ModuleEnvironment(
    ast=tree,
    instance=instance,
    kind=kind,
    name=name,
    path=path,
    source=source,
    relative_path=relative_path,
  )


def identify_node(module: ast.Module, area: FrameArea):
  line_start = area.line_start
  line_end = area.line_end

  if (line_start is None) or (line_end is None):
    return None

  def node_matches(node: ast.expr | ast.stmt):
    # Line numbers start at 1 and both ends are inclusive, for both AST nodes and exceptions

    if node.end_lineno is None:
      return False

    # print(node, (node.lineno, node.end_lineno), (line_start, line_end))
    # print(node, (node.col_offset, node.end_col_offset), (col_start, col_end))

    if not ((node.lineno <= line_start) and (node.end_lineno >= line_end)):
      return False

    if (area.col_start is not None) and (node.lineno == line_start) and (node.col_offset > area.col_start):
      # print('>', node.col_offset, col_start)
      return False

    if (area.col_end is not None) and (node.end_col_offset is not None) and (node.end_lineno == line_end) and (node.end_col_offset < area.col_end):
      # print('>', node, node.end_lineno, line_end, node.end_col_offset, col_end)
      return False

    return True


  current_node: AstNode = module
  parent_nodes = list[AstNode]()

  while True:
    children_candidates = list[ast.expr | ast.stmt]()
    nonchildren_candidates = list[ast.expr | ast.stmt]()

    match current_node:
      case ast.Call(func, args, keywords):
        nonchildren_candidates = [func, *args] + [keyword.value for keyword in keywords]
      case ast.ClassDef(name, bases, keywords, body, decorator_list, type_params):
        children_candidates += body
        children_candidates += decorator_list
        children_candidates += bases
      case ast.Expr(value):
        nonchildren_candidates.append(value)
      case ast.AsyncFunctionDef(body=body) | ast.FunctionDef(body=body):
        children_candidates += body
      case ast.If(test, body, orelse):
        children_candidates += [test, *body, *orelse]
      case ast.Module(body=body):
        children_candidates += body
      case ast.AsyncFor(target, iter, body, orelse, type_comment) | ast.For(target, iter, body, orelse, type_comment):
        children_candidates += [target, iter, *body, *orelse]
      case ast.Try(body, handlers, orelse, finalbody) | ast.TryStar(body, handlers, orelse, finalbody):
        children_candidates += [*body, *orelse, *finalbody]
        nonchildren_candidates += [handler.type for handler in handlers]

        for handler in handlers:
          children_candidates += handler.body
      case ast.AsyncWith(items, body, type_comment) | ast.With(items, body, type_comment):
        children_candidates += (item.context_expr for item in items)
        children_candidates += body

    children_candidates_matching = [candidate for candidate in children_candidates if (candidate is not None) and node_matches(candidate)]
    nonchildren_candidates_matching = [candidate for candidate in nonchildren_candidates if (candidate is not None) and node_matches(candidate)]

    if (len(children_candidates_matching) == 1) and not nonchildren_candidates_matching:
      parent_nodes.append(current_node)
      current_node = children_candidates_matching[0]
    elif (len(nonchildren_candidates_matching) == 1) and not children_candidates_matching:
      current_node = nonchildren_candidates_matching[0]
    else:
      return AstTarget(current_node, parent_nodes)
