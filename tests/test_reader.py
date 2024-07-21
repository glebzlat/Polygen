from io import StringIO

import unittest

from polygen.parser import Reader, Token


class ReaderTest(unittest.TestCase):
    def test_read_string(self):
        s = "hello world"
        r = Reader(s)

        clue = s
        self.assertFalse(r.eof)
        self.assertEqual(list(clue), list(r))
        self.assertEqual(r.name, "<string>")
        self.assertTrue(r.eof)

    def test_read_stream(self):
        s = "hello world"
        stream = StringIO(s)
        r = Reader(stream)

        clue = s
        self.assertFalse(r.eof)
        self.assertEqual(list(clue), list(r))
        self.assertEqual(r.name, "<stream>")
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

    def test_token(self):
        s = """abc
def
        """
        r = Reader(s)

        tokens = [
            Token("a", line=1, start=0, end=1, filename="<string>"),
            Token("b", line=1, start=1, end=2, filename="<string>"),
            Token("c", line=1, start=2, end=3, filename="<string>"),
            Token("\n", line=1, start=3, end=4, filename="<string>"),
            Token("d", line=2, start=0, end=1, filename="<string>"),
            Token("e", line=2, start=1, end=2, filename="<string>"),
            Token("f", line=2, start=2, end=3, filename="<string>")
        ]

        self.assertEqual("a", tokens[0])

        def token_attrs(tok: Token):
            return (tok.value, tok.line, tok.start, tok.end, tok.filename)

        result = list(r)
        for a, b in zip(tokens, result):
            self.assertEqual(token_attrs(a), token_attrs(b))
