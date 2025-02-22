import ast
from dataclasses import dataclass
import inspect
import itertools
from pathlib import Path
from pprint import pprint
import sys
from types import CodeType, ModuleType, TracebackType
from typing import Literal, Optional


@dataclass(slots=True)
class ExceptionItem:
  message: str

type AstNode = ast.Module | ast.expr | ast.stmt
type ModuleKind = Literal['internal', 'std', 'lib', 'user']

@dataclass(slots=True)
class ModuleItem:
  ast: Optional[ast.Module]
  instance: Optional[ModuleType]
  kind: ModuleKind
  name: str
  path: Path

@dataclass(slots=True)
class FrameItem:
  module: ModuleItem
  node: Optional[AstNode]
  reraise: bool


def extract(start_exc: BaseException, /):
  # List exceptions
  # Re-raised exceptions form a single exception and cannot be detected at this stage.

  current_exc = start_exc
  excs = list[tuple[BaseException, Literal['base', 'cause', 'context']]]()
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


  for exc, exc_kind in excs:
    # List frames

    current_tb = exc.__traceback__
    tbs = list[TracebackType]()

    while current_tb:
      tbs.append(current_tb)
      current_tb = current_tb.tb_next


    # Detect syntax error

    frames = list[FrameItem]()
    is_syntax_error = False # isinstance(exc, SyntaxError)

    if is_syntax_error:
      file.write(format_frame(
        escape=escape,
        frame_index=0,
        func_name=Path(exc.filename).name,
        prefix=prefix,
        raw_path=exc.filename,
        positions=(
          exc.lineno,
          exc.end_lineno,
          (exc.offset - 1) if exc.offset is not None else None,
          (
            (exc.end_offset - 1) if exc.end_offset > 0 else exc.offset
          ) if exc.end_offset is not None else None
        ),
        options=options
      ))


    # Extract frames

    for tb_index, tb in enumerate(reversed(tbs)):
      frame = tb.tb_frame
      frame_code = frame.f_code
      raw_path = frame_code.co_filename

      positions = next(
        itertools.islice(frame_code.co_positions(), tb.tb_lasti // 2, None)
      ) if tb.tb_lasti >= 0 else None

      # print()
      # print()
      # print()
      # print(frame_code)
      # print(inspect.getmodule(frame_code))
      # print()
      # print()
      # print()
      # print(frame_code.co_name, inspect.getmodule(frame_code).__name__)

      frames.append(extract_frame(
        code=frame_code,
        frame_index=(tb_index + (1 if is_syntax_error else 0)),
        func_name=frame_code.co_qualname,
        raw_path=raw_path,
        positions=positions,
      ))

    pprint(frames)



def extract_module_from_code(code: CodeType):
  instance = inspect.getmodule(code)

  if instance is None:
    return extract_module_from_path(Path(code.co_filename))

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
      node = identify_node(module_item.ast, line_start, line_end, col_start, col_end)
    else:
      node = None
  else:
    node = None

  # print('Frame')
  # print(f'{kind=} {module_name=}')
  # print('Node:', ast.unparse(node))
  # print()

  return FrameItem(
    module=module_item,
    node=node,
    reraise=((frame_index > 0) and isinstance(node, ast.Raise)),
  )


def identify_node(mod: ast.Module, line_start: int, line_end: int, col_start: Optional[int], col_end: Optional[int]) -> AstNode:
  best_candidate: ast.Module | ast.expr | ast.stmt = mod

  def node_matches(node: ast.expr | ast.stmt):
    # Line numbers start at 1

    if node.end_lineno is None:
      return False

    if not ((node.lineno <= line_start) and (node.end_lineno >= line_end)):
      return False

    if (col_start is not None) and (col_end is not None) and (node.end_col_offset is not None):
      if not ((node.col_offset <= col_start) and (node.end_col_offset >= col_end)):
        return False

    return True


  while True:
    new_candidates = list[ast.expr | ast.stmt]()

    match best_candidate:
      case ast.Call(func, args, keywords):
        new_candidates += [func, *args]
        new_candidates += (keyword.value for keyword in keywords)
      case ast.ClassDef(body=body):
        new_candidates += body
      case ast.ExceptHandler(type, name, body):
        new_candidates += [type, *body]
      case ast.Expr(value):
        new_candidates.append(value)
      case ast.AsyncFunctionDef(body=body) | ast.FunctionDef(body=body):
        new_candidates += body
      case ast.If(test, body, orelse):
        new_candidates += [test, *body, *orelse]
      case ast.Module(body=body):
        new_candidates += body
      case ast.For(target, iter, body, orelse, type_comment):
        new_candidates += [target, iter, *body, *orelse]
      case ast.Try(body, handlers, orelse, finalbody) | ast.TryStar(body, handlers, orelse, finalbody):
        new_candidates += [*body, *handlers, *orelse, *finalbody]
      case ast.With(items, body, type_comment):
        new_candidates += (item.context_expr for item in items)
        new_candidates += body
      case _:
        return best_candidate


    candidates_matching = [candidate for candidate in new_candidates if (candidate is not None) and node_matches(candidate)]
    # print('>', best_candidate, new_candidates, candidates_matching)

    if len(candidates_matching) == 1:
      best_candidate = candidates_matching[0]
    else:
      return best_candidate
