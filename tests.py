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


for test in [
  test1,
  test2,
  test3,
  # test4,
  test5,
]:
  try:
    test()
  except Exception as e:
    dump(e, sys.stdout)

  print('-' * 80)
