import unittest

from polygen.utility import wrap_string, reindent


class TestWrapString(unittest.TestCase):
    def test_simple_case(self):
        self.assertEqual(wrap_string('abc'), '"abc"')

    def test_single_quotes(self):
        self.assertEqual(wrap_string('abc', double=False), "'abc'")

    def test_string_with_quote_single(self):
        self.assertEqual(wrap_string("'", double=False), "'\\''")

    def test_string_with_quote_double(self):
        self.assertEqual(wrap_string('"'), '"\\""')

    def test_backslash(self):
        self.assertEqual(wrap_string('\\'), '"\\"')


class TestReindent(unittest.TestCase):
    def test_level_1(self):
        s = """
a
b
c
"""
        clue = """
    a
    b
    c
"""
        self.assertEqual(reindent(s, level=1), clue)

    def test_level_0(self):
        s = """
    a
    b
    c
"""
        clue = """
a
b
c
"""
        self.assertEqual(reindent(s, level=0), clue)

    def test_multiple_indents(self):
        s = """
def func():
  print("hello")
"""
        clue = """
            def func():
              print("hello")
"""
        self.assertEqual(reindent(s, level=3), clue)

    def test_empty_lines(self):
        s = """
hello

world
"""
        clue = """
        hello

        world
"""
        self.assertEqual(reindent(s, level=2), clue)

    def test_indented(self):
        s = """
    hello
"""
        clue = """
                hello
"""
        self.assertEqual(reindent(s, level=4), clue)

    def test_higher_indent_first(self):
        s = """
    first line
  second line
"""
        clue = """
      first line
    second line
"""
        self.assertEqual(reindent(s, level=1), clue)
