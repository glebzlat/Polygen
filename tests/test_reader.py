from io import StringIO

import unittest

from polygen.reader import Reader


class ReaderTest(unittest.TestCase):
    def test_read_string(self):
        s = "hello world"
        r = Reader(s)

        clue = s + '\0'
        self.assertFalse(r.eof)
        self.assertEqual(list(clue), list(r))
        self.assertEqual(r.name, "<unicode string>")
        self.assertTrue(r.eof)

    def test_read_stream(self):
        s = "hello world"
        stream = StringIO(s)
        r = Reader(stream)

        clue = s + '\0'
        self.assertFalse(r.eof)
        self.assertEqual(list(clue), list(r))
        self.assertEqual(r.name, "<file>")
        self.assertTrue(r.eof)

    def test_line_count(self):
        s = "line 1\nline2\nline3"
        r = Reader(s)
        _ = list(r)

        self.assertEqual(r.line, 3)

    def test_column_count(self):
        s = "123456"
        r = Reader(s)
        _ = list(r)

        self.assertEqual(r.column, 6)
