import ast
import functools
import inspect
import itertools
import sys
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from types import CodeType, ModuleType, TracebackType
from typing import Literal, Optional, Sequence


type AstNode = ast.Module | ast.expr | ast.stmt

@dataclass(slots=True)
class AstTarget:
  node: AstNode
  parents: Sequence[AstNode]


type ModuleKind = Literal['internal', 'std', 'lib', 'user']

@dataclass(frozen=True, slots=True)
class ModuleItem:
  ast: Optional[ast.Module]
  instance: Optional[ModuleType]
  kind: ModuleKind
  name: str
  path: Path

@dataclass(eq=True, frozen=True, slots=True)
class FrameItem:
  module: ModuleItem
  target: Optional[AstTarget]
  reraise: bool


type ExceptionKind = Literal['base', 'cause', 'context']

@dataclass(slots=True)
class ExceptionItem:
  children: 'Sequence[ExceptionChain]'
  frames: Sequence[FrameItem]
  instance: BaseException
  kind: ExceptionKind

@dataclass(slots=True)
class ExceptionChain:
  excs: Sequence[ExceptionItem]


def extract(start_exc: BaseException, /):
  return extract_exc_chain(start_exc)

def extract_exc_chain(start_exc: BaseException, /):
  current_exc = start_exc

  excs = list[tuple[BaseException, ExceptionKind]]()
  excs.append((current_exc, 'base'))

  while True:
    if current_exc.__cause__:
      current_exc = current_exc.__cause__
      excs.append((current_exc, 'cause'))
    elif current_exc.__context__:
      current_exc = current_exc.__context__
      excs.append((current_exc, 'context'))
    else:
      break

  def map_exc(exc: BaseException, exc_kind: ExceptionKind):
    return ExceptionItem(
      children=([extract_exc_chain(exc) for exc in exc.exceptions] if isinstance(exc, BaseExceptionGroup) else []),
      frames=extract_exc_frames(exc),
      instance=exc,
      kind=exc_kind,
    )

  return ExceptionChain([map_exc(exc, exc_kind) for exc, exc_kind in excs])



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
    raw_path = frame_code.co_filename

    positions = next(
      itertools.islice(frame_code.co_positions(), tb.tb_lasti // 2, None)
    ) if tb.tb_lasti >= 0 else None

    frame = extract_frame(
      code=frame_code,
      frame_index=(tb_index + (1 if is_syntax_error else 0)),
      func_name=frame_code.co_qualname,
      raw_path=raw_path,
      positions=positions,
    )

    frames.append(frame)

  return frames



def extract_module_from_code(code: CodeType):
  instance = inspect.getmodule(code)

  if instance is None:
    return extract_module_from_path(Path(code.co_filename))

  return extract_module_from_module(instance)

@functools.cache
def extract_module_from_module(instance: ModuleType):
  name = instance.__name__
  segments = name.split('.')
  path = Path(inspect.getfile(instance))

  # kind = 'internal' if module_name.startswith('<') else 'user'

  if segments[0] in sys.builtin_module_names:
    kind = 'std'
  else:
    try:
      path.relative_to(Path.cwd())
    except ValueError:
      kind = 'lib'
    else:
      kind = 'user'

  return ModuleItem(
    ast=ast.parse(inspect.getsource(instance)),
    instance=instance,
    kind=kind,
    name=name,
    path=path,
  )

@functools.cache
def extract_module_from_path(path: Path):
  name = inspect.getmodulename(path)

  if name is None:
    return None

  # try:
  #   frame_contents = path.read_text()
  # except OSError:
  #   frame_contents = None

  # Alternative
  # frame_contents = inspect.getsourcefile(sys.modules[module_name])

  return ModuleItem(
    ast=None,
    instance=None,
    kind='user',
    name=name,
    path=path,
  )


def extract_frame(
  code: Optional[CodeType],
  frame_index: int,
  func_name: str,
  raw_path: str,
  positions: Optional[tuple[Optional[int], Optional[int], Optional[int], Optional[int]]],
):
  # if raw_path[0] == '<':
  #   kind = 'internal'
  #   frame_path = None
  #   module_name = raw_path
  # else:
  #   # Locate module

  #   frame_path = Path(raw_path)

  #   for sys_path in sys.path:
  #     try:
  #       rel_path = frame_path.relative_to(sys_path)
  #     except ValueError:
  #       pass
  #     else:
  #       *directories, file_name = rel_path.parts

  #       module_path = directories + [file_name.removesuffix('.py')]
  #       module_name = '.'.join(module_path)

  #       if module_path[0] in sys.stdlib_module_names:
  #         kind = 'std'
  #       else:
  #         try:
  #           frame_path.relative_to(Path.cwd())
  #         except ValueError:
  #           kind = 'lib'
  #         else:
  #           kind = 'user'

  #       break
  #   else:
  #     kind = 'user'
  #     module_name = raw_path

  module_item = extract_module_from_code(code) if code is not None else None

  # print(extract_module_from_code(code))
  # print(extract_module_from_path(Path(code.co_filename)))
  # print()


  # Extract AST node

  if (module_item is not None) and (module_item.ast is not None) and (positions is not None):
    line_start, line_end, col_start, col_end = positions
    # code_lines = frame_contents.splitlines()

    if (line_start is not None) and (line_end is not None):
      target = identify_node(module_item.ast, line_start, line_end, col_start, col_end)
    else:
      target = None
  else:
    target = None

  # print('Frame')
  # print(f'{kind=} {module_name=}')
  # print('Node:', ast.unparse(target.node))
  # print()

  return FrameItem(
    module=module_item,
    target=target,
    reraise=((frame_index > 0) and isinstance(target, ast.Raise)),
  )


def identify_node(module: ast.Module, line_start: int, line_end: int, col_start: Optional[int], col_end: Optional[int]):
  def node_matches(node: ast.expr | ast.stmt):
    # Line numbers start at 1 and both ends are inclusive, for both AST nodes and exceptions

    if node.end_lineno is None:
      return False

    # print(node, (node.lineno, node.end_lineno), (line_start, line_end))
    # print(node, (node.col_offset, node.end_col_offset), (col_start, col_end))

    if not ((node.lineno <= line_start) and (node.end_lineno >= line_end)):
      return False

    if (col_start is not None) and (node.lineno == line_start) and (node.col_offset > col_start):
      # print('>', node.col_offset, col_start)
      return False

    if (col_end is not None) and (node.end_col_offset is not None) and (node.end_lineno == line_end) and (node.end_col_offset < col_end):
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
        nonchildren_candidates += bases
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
      case _:
        return AstTarget(current_node, parent_nodes)

    children_candidates_matching = [candidate for candidate in children_candidates if (candidate is not None) and node_matches(candidate)]
    nonchildren_candidates_matching = [candidate for candidate in nonchildren_candidates if (candidate is not None) and node_matches(candidate)]
    # print('>', best_candidate, new_candidates, candidates_matching)

    if (len(children_candidates_matching) == 1) and not nonchildren_candidates_matching:
      parent_nodes.append(current_node)
      current_node = children_candidates_matching[0]
    elif (len(nonchildren_candidates_matching) == 1) and not children_candidates_matching:
      current_node = nonchildren_candidates_matching[0]
    else:
      return AstTarget(current_node, parent_nodes)
