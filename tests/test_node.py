import unittest

from polygen.node import (
    Grammar,
    Rule,
    Expression,
    Identifier,
    Alt,
    Part,
    Literal,
    Char,
    GrammarVisitor,
    common_prefix,
    has_prefix
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


class MiscTest(unittest.TestCase):
    def test_common_prefix(self):
        A, B, C, D = Char('a'), Char('b'), Char('c'), Char('d')
        lhs = Literal([A, B, C])
        rhs = Literal([A, B, D])

        clue = [A, B]
        result = common_prefix(lhs, rhs)
        self.assertEqual(result, clue)

    def test_has_prefix(self):
        A, B, C = Char('a'), Char('b'), Char('c')
        lit = Literal([A, B, C])

        self.assertTrue(has_prefix([], lit))
        self.assertTrue(has_prefix([A], lit))
        self.assertTrue(has_prefix([A, B], lit))
        self.assertFalse(has_prefix([B], lit))


class TestVisitor(unittest.TestCase):
    def test_collect_chars(self):

        class Visitor(GrammarVisitor):
            def visit_Char(self, node: Char, charlist: list[Char]):
                charlist.append(node)

        J, O, Y = Char('j'), Char('o'), Char('y')
        PJ, PO, PY = (Expression([Alt([Part(prime=c)])]) for c in (J, O, Y))

        def rule(name, exp):
            return Rule(Identifier(name), Expression(exp))

        grammar = Grammar([rule('j', PJ), rule('o', PO), rule('y', PY)])
        visitor = Visitor()
        clue = [J, O, Y]
        result = []
        visitor.visit(grammar, result)

        self.assertEqual(result, clue)

