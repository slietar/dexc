import sys
from dexc import dump, install


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
  raise ExceptionGroup('Group', [
    Exception('A'),
    Exception('B'),
    Exception('C'),
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
]:
  print(f'-- {test.__name__} {'-' * 80}')

  try:
    test()
  except Exception as e:
    dump(e, sys.stdout)
