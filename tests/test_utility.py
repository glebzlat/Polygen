import unittest

from polygen.utility import wrap_string, reindent


class TestWrapString(unittest.TestCase):
    def test_auto_wo_quotes(self):
        self.assertEqual(wrap_string("abc", "auto"), "'abc'")

    def test_auto_single_quotes(self):
        self.assertEqual(wrap_string("'", "auto"), '"\'"')

    def test_auto_single_double_quotes(self):
        self.assertEqual(wrap_string("'\"", "auto"), "'\\'\"'")

    def test_single_mode_wo_quotes(self):
        self.assertEqual(wrap_string("abc", "single"), "'abc'")

    def test_single_mode_w_single_quotes(self):
        self.assertEqual(wrap_string("'", "single"), '"\'"')

    def test_single_mode_w_single_double(self):
        self.assertEqual(wrap_string("'\"", "single"), "'\\'\"'")

    def test_double_mode_w_double_quotes(self):
        self.assertEqual(wrap_string('"', "double"), "'\"'")

    def test_double_mode_w_single_double(self):
        self.assertEqual(wrap_string("'\"", "double"), '"\'\\""')

    def test_force_single_wo_quotes(self):
        self.assertEqual(wrap_string("abc", "force_single"), "'abc'")

    def test_force_single_w_single(self):
        self.assertEqual(wrap_string("'", "force_single"), "'\\''")

    def test_force_double_wo_quotes(self):
        self.assertEqual(wrap_string("abc", "force_double"), '"abc"')

    def test_force_double_w_double(self):
        self.assertEqual(wrap_string('"', "force_double"), '"\\""')


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
