import unittest

from polygen.node import (
    Grammar,
    Rule,
    Expression,
    Identifier,
    Alt,
    Part,
    Literal,
    Char
)


class TestDescendants(unittest.TestCase):
    def test_char(self):
        tree = Char('a')

        clue = [tree]
        self.assertEqual(list(tree.descendants), clue)

    def test_literal(self):
        A, B, C = Char('a'), Char('b'), Char('c')
        tree = Literal([A, B, C])

        clue = [tree, A, B, C]
        self.assertEqual(list(tree.descendants), clue)

    def test_alt(self):
        A, B, C = Char('a'), Char('b'), Char('c')
        PA, PB, PC = Part(prime=A), Part(prime=B), Part(prime=C)
        tree = Alt([PA, PB, PC])

        clue = [tree, PA, A, PB, B, PC, C]
        self.assertEqual(list(tree.descendants), clue)

    def test_grammar(self):
        A, B, C = Char('a'), Char('b'), Char('c')
        PA, PB, PC = Part(prime=A), Part(prime=B), Part(prime=C)
        ALT = Alt([PA, PB, PC])
        EXP = Expression([ALT])
        RULE = Rule(Identifier("rule"), EXP)
        tree = Grammar([RULE])

        clue = [tree, RULE, EXP, ALT, PA, A, PB, B, PC, C]
        self.assertEqual(list(tree.descendants), clue)
