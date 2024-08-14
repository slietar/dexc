from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from dexc import dump


# Base test

def test1():
  raise Exception


# Using __context__

def test2():
  try:
    raise Exception('A')
  except:
    raise Exception('B')


# Using __cause__

def test3():
  try:
    raise Exception('A')
  except Exception as e:
    raise Exception('B') from e


# Recursion error

def test4():
  def a():
    a()

  a()


# Exception group

def test5():
  def produce_exc(name: str):
    try:
      raise Exception(name)
    except Exception as e:
      return e

  raise ExceptionGroup('Group', [
    produce_exc('A'),
    produce_exc('B'),
    Exception('C'),
    ExceptionGroup('Group2', [
      produce_exc('D'),
      produce_exc('E')
    ]),
    Exception('D'),
  ])


# Frame in locals

def test6():
  def a():
    raise Exception

  a()


# Large number of lines in a frame

def test7():
  raise Exception([ # 1
    # 2
    # 3
    # 4
    # 5
  ])

  # Hi


# Concatenated traces after re-raising an exception

def test8():
  try:
    raise Exception
  except Exception as e:
    raise e


# Syntax error

def test9():
  with TemporaryDirectory(delete=False) as dir_path:
    module_name = 'test9'
    (Path(dir_path) / f'{module_name}.py').write_text('# Hi\nhello(')

    sys.path.append(dir_path)

    __import__(module_name)


# ---


for test in [
  test1,
  test2,
  test3,
  # test4,
  test5,
  test6,
  test7,
  test8,
  test9,
]:
  print(f'-- {test.__name__} {'-' * 80}')

  try:
    test()
  except Exception as e:
    dump(e, sys.stdout)
