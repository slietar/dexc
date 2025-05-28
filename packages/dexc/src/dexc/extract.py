from abc import ABC
import ast
import builtins
import functools
import itertools
from dataclasses import dataclass, field
from types import NoneType, TracebackType
from typing import Iterable, Literal, Optional, TypeAlias

from .inspector import ModuleInfo, ModuleInspector, PartialSource


AncestorKind: TypeAlias = Literal['class', 'function', 'method']
AstNode: TypeAlias = ast.Module | ast.expr | ast.stmt

@dataclass(frozen=True, slots=True)
class Ancestor:
  kind: AncestorKind
  name: str

@dataclass(frozen=True, slots=True)
class AstTarget:
  node: AstNode
  parents: list[AstNode] = field(hash=False) # Includes node

  def ancestors(self) -> Iterable[Ancestor]:
    prev_class = False

    for parent_node in self.parents:
      match parent_node:
        case ast.AsyncFunctionDef(name=name) | ast.FunctionDef(name=name):
          yield Ancestor('method' if prev_class else 'function', name)
          prev_class = False
        case ast.ClassDef(name=name):
          yield Ancestor('class', name)
          prev_class = True


@dataclass(frozen=True, slots=True)
class FrameArea(ABC):
  # Line numbers start at 1 and both ends are inclusive
  # Column numbers start at 0 and only the start is inclusive

  line_start: int
  line_end: Optional[int] = field(default=None, init=False)
  col_start: Optional[int] = field(default=None, init=False)
  col_end: Optional[int] = field(default=None, init=False)

@dataclass(frozen=True, slots=True)
class FrameAreaStartLine(FrameArea):
  pass

@dataclass(frozen=True, slots=True)
class FrameAreaStartLineCol(FrameArea):
  col_start: int

@dataclass(frozen=True, slots=True)
class FrameAreaLines(FrameArea):
  line_end: int
  col_start: NoneType = field(default=None, init=False)

@dataclass(frozen=True, slots=True)
class FrameAreaFull(FrameArea):
  line_end: int
  col_start: int
  col_end: int

def create_frame_area(
  line_start: Optional[int],
  line_end: Optional[int],
  col_start: Optional[int],
  col_end: Optional[int],
) -> Optional[FrameArea]:
  match line_start, line_end, col_start, col_end:
    case builtins.int(), builtins.int(), builtins.int(), builtins.int():
      return FrameAreaFull(line_start, line_end, col_start, col_end)
    case builtins.int(), builtins.int(), _, _:
      return FrameAreaLines(line_start, line_end)
    case builtins.int(), _, builtins.int(), _:
      return FrameAreaStartLineCol(line_start, col_start)
    case builtins.int(), _, _, _:
      return FrameAreaStartLine(line_start)
    case _:
      return None


@dataclass(eq=True, frozen=True, slots=True)
class FrameItem:
  area: Optional[FrameArea]
  hidden: bool
  module: ModuleInfo
  target: Optional[AstTarget]
  target_is_module: bool # Indicates whether the target is the module's root (should not be used unless target is None)
  target_name: Optional[str]
  reraise: bool

  @property
  def important(self):
    return self.module.kind == 'user'

  @property
  def traceable(self):
    return (self.module.source is not None) and (self.area is not None)


ExceptionChainRelation: TypeAlias = Literal['cause', 'context']

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



@functools.cache
def get_inspector():
  return ModuleInspector()

def extract_exc_frames(exc: BaseException, /):
  # Outermost frames are first
  frames = list[FrameItem]()

  if exc.__traceback__:
    frames += extract_tb_frames(exc.__traceback__)

  # Detect syntax error
  if isinstance(exc, SyntaxError) and (exc.filename is not None):
    module_info = get_inspector().inspect(
      exc.filename,
      partial_source=(
        PartialSource(
          contents=exc.text,
          start_line=exc.lineno,
        ) if (
          (exc.text is not None) and
          (exc.lineno is not None)
        ) else None
      ),
      previous_frame=(frames[-1] if frames else None),
    )

    area = create_frame_area(
      line_start=exc.lineno,
      line_end=exc.end_lineno,
      col_start=(exc.offset - 1 if exc.offset is not None else None),
      col_end=(
        (exc.end_offset if (exc.end_offset > 0) else exc.offset)
        if exc.end_offset is not None
        else None
      ),
    )

    frame = FrameItem(
      area=area,
      hidden=False,
      module=module_info,
      reraise=False,
      target=None,
      target_is_module=(module_info.name_segments is not None),
      target_name=None,
    )

    frames.append(frame)

  return frames


def extract_tb_frames(start_tb: TracebackType, /):
  current_tb = start_tb
  tbs = list[TracebackType]()

  while current_tb:
    tbs.append(current_tb)
    current_tb = current_tb.tb_next


  # Extract frames

  inspector = get_inspector()
  frames = list[FrameItem]() # Outermost frames are first

  for tb_index, tb in enumerate(tbs):
    frame = tb.tb_frame
    frame_code = frame.f_code

    positions = next(
      itertools.islice(frame_code.co_positions(), tb.tb_lasti // 2, None)
    ) if tb.tb_lasti >= 0 else None

    area = create_frame_area(*positions) if positions is not None else None
    module_info = inspector.inspect(frame.f_code.co_filename, frame, previous_frame=(frames[-1] if frames else None))

    if (module_info.ast is not None) and (area is not None):
      target = identify_node(module_info.ast, area)
    else:
      target = None

    hidden = (
      bool(local_hidden)
      if (local_hidden := frame.f_locals.get('__tracebackhide__')) is not None
      else bool(frame.f_globals.get('__tracebackhide__'))
    )

    if frame.f_code.co_name == '<module>':
      target_is_module = True
      target_name = None
    else:
      target_is_module = False
      target_name = frame.f_code.co_name

    frame = FrameItem(
      area=area,
      hidden=hidden,
      module=module_info,
      target=target,
      target_is_module=target_is_module,
      target_name=target_name,
      reraise=((tb_index < len(tbs) - 1) and (target is not None) and isinstance(target.node, ast.Raise)),
    )

    frames.append(frame)

  return frames


def identify_node(module: ast.Module, area: FrameArea):
  line_start = area.line_start
  line_end = area.line_end

  if line_end is None:
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
      case ast.ClassDef(name, bases, keywords, body, decorator_list):
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
