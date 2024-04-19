import unittest

from polygen.parser import Parser
from polygen.reader import Reader


class TestParser(unittest.TestCase):
    def test_peek(self):
        s = "123456"
        r = Reader(s)
        p = Parser(r)

        self.assertEqual(p._peek_char(), '1')
        self.assertEqual(p._peek_char(), '1')
        self.assertEqual(p._mark(), 0)

    def test_get(self):
        s = "123456"
        r = Reader(s)
        p = Parser(r)

        self.assertEqual(p._get_char(), '1')
        self.assertEqual(p._get_char(), '2')
        self.assertEqual(p._mark(), 2)

    def test_reset(self):
        s = "123456"
        r = Reader(s)
        p = Parser(r)

        pos = p._mark()
        for _ in range(3):
            p._get_char()

        self.assertEqual(p._mark(), 3)
        self.assertEqual(p._peek_char(), '4')

        p._reset(pos)
        self.assertEqual(p._mark(), 0)
        self.assertEqual(p._peek_char(), '1')

    def test_expect(self):
        s = "123456"
        r = Reader(s)
        p = Parser(r)

        self.assertEqual(p._expect('1'), '1')
        self.assertEqual(p._expect('2'), '2')
        self.assertEqual(p._expect('3'), '3')
        self.assertEqual(p._mark(), 3)

        self.assertIsNone(p._expect('5'))
        self.assertEqual(p._mark(), 3)
