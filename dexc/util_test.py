from typing import Iterable
import unittest

from .util import format_condensed_seq, wrap_into_ellipsis, wrap_into_paragraph


class TestUtil(unittest.TestCase):
  def test_format_condensed_seq(self):
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (0, 0), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (1, 1), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (2, 2), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (3, 3), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/b/c')

    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (0, 3), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], '...')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (1, 3), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/...')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (2, 3), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/b/...')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (0, 1), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], '.../b/c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (0, 2), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], '.../c')
    self.assertEqual(format_condensed_seq(['a', 'b', 'c'], [1, 1, 1], (1, 2), ellipsis='...', ellipsis_width=1, separator='/', separator_width=1)[0], 'a/.../c')

  def test_wrap_into_ellipsis(self):
     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='...', width=6),
        'foobar',
     )

     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='...', width=5),
        'fo...',
     )

     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='/', width=6),
        'foobar',
     )

     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='/', width=5),
        'foob/',
     )

     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='/', margin=1, width=7),
        'foobar',
     )

     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='/', margin=1, width=6),
        'fooba/',
     )

     self.assertEqual(
        wrap_into_ellipsis('foobar', ellipsis='/', margin=1, width=5),
        'foob/',
     )

  def test_wrap_into_paragraph(self):
    def first_item(tup: Iterable[tuple[str, int]]):
      for item, _ in tup:
        yield item

    self.assertEqual(
      list(first_item(wrap_into_paragraph('  Lorem ipsum dolor sit amet, consectetur adipisci elit.', width=12))),
      ['  Lorem', '  ipsum', '  dolor sit', '  amet,', '  consectetu', '  r adipisci', '  elit.'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo bar', width=3))),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo bar', width=2))),
      ['fo', 'o', 'ba', 'r'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo  bar', width=3))),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo  bar', width=4))),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo  bar', width=7))),
      ['foo', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo  bar', width=8))),
      ['foo  bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo-bar', width=5))),
      ['foo-', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo_bar', width=5))),
      ['foo_', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo barbarbar', width=6))),
      ['foo', 'barbar', 'bar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo barbarbar', max_trailing_whitespace=1, width=6))),
      ['foo ba', 'rbarba', 'r'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foobar      ', width=6))),
      ['foobar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foobar ', width=4))),
      ['foob', 'ar'],
    )

    self.assertEqual(
      list(first_item(wrap_into_paragraph('foo      bar', width=3))),
      ['foo', 'bar'],
    )


if __name__ == '__main__':
    unittest.main()
