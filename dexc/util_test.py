import unittest

from .util import wrap_line


class TestUtil(unittest.TestCase):
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
