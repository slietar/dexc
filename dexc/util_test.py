import unittest

from .util import format_condensed_seq, wrap_line


class TestUtil(unittest.TestCase):
  def test_format_condensed_seq(self):
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (0, 0), ellipsis='...', separator='/'), 'a/b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (1, 1), ellipsis='...', separator='/'), 'a/b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (2, 2), ellipsis='...', separator='/'), 'a/b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (3, 3), ellipsis='...', separator='/'), 'a/b/c')

    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (0, 3), ellipsis='...', separator='/'), '...')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (1, 3), ellipsis='...', separator='/'), 'a/...')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (2, 3), ellipsis='...', separator='/'), 'a/b/...')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (0, 1), ellipsis='...', separator='/'), '.../b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (0, 2), ellipsis='...', separator='/'), '.../c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], (1, 2), ellipsis='...', separator='/'), 'a/.../c')

  def test_wrap_line(self):
    self.assertEqual(
      list(wrap_line('  Lorem ipsum dolor sit amet, consectetur adipisci elit.', width=12)),
      ['  Lorem', '  ipsum', '  dolor sit', '  amet,', '  consectetu', '  r adipisci', '  elit.'],
    )

    self.assertEqual(
      list(wrap_line('foo bar', width=3)),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(wrap_line('foo bar', width=2)),
      ['fo', 'o', 'ba', 'r'],
    )

    self.assertEqual(
      list(wrap_line('foo  bar', width=3)),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(wrap_line('foo  bar', width=4)),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(wrap_line('foo  bar', width=7)),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(wrap_line('foo  bar', width=8)),
      ['foo  bar'],
    )


if __name__ == '__main__':
    unittest.main()
