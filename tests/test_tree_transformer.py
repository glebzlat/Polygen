import unittest

from itertools import repeat

from polygen.node import (
    Grammar,
    Rule,
    Identifier,
    Expression,
    Alt,
    Part,
    Class,
    Range,
    And,
    Not,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    Char
)

from polygen.errors import (
    Errors,
    TreeTransformerError,
)

from polygen.tree_transformer import (
    ExpandClassRule,
    ReplaceRepRule,
    ReplaceZeroOrOneRule,
    ReplaceOneOrMore,
    EliminateAndRule,
    CheckUndefRedefRule,
    ReplaceNestedExpsRule,
    # TreeWriter  # TODO: test
)


class TestExpandClassRule(unittest.TestCase):
    def test_simple_range(self):
        A = Char('a')
        tree = Part(prime=Class(Range(A)))
        clue = Part(prime=Expression(Alt(Part(prime=A))))
        rule = ExpandClassRule()

        node = tree.prime
        rule.visit_Class(node)
        self.assertEqual(tree, clue)
        self.assertEqual(tree.prime.parent, tree)

    def test_range_abc(self):
        A, B, C = Char('a'), Char('b'), Char('c')
        tree = Part(prime=Class(Range(A, C)))
        clue = Part(
            prime=Expression(
                Alt(Part(prime=A)),
                Alt(Part(prime=B)),
                Alt(Part(prime=C))
            )
        )
        rule = ExpandClassRule()

        node = tree.prime
        rule.visit_Class(node)
        self.assertEqual(tree, clue)
        self.assertEqual(tree.prime.parent, tree)

    def test_two_ranges(self):
        A, B, C = Char('a'), Char('b'), Char('c')
        _0, _1, _2 = Char('0'), Char('1'), Char('2')
        tree = Part(prime=Class(Range(A, C), Range(_0, _2)))
        clue = Part(
            prime=Expression(
                Alt(Part(prime=_0)),
                Alt(Part(prime=_1)),
                Alt(Part(prime=_2)),
                Alt(Part(prime=A)),
                Alt(Part(prime=B)),
                Alt(Part(prime=C))
            )
        )
        rule = ExpandClassRule()

        node = tree.prime
        rule.visit_Class(node)
        self.assertEqual(tree, clue)
        self.assertEqual(tree.prime.parent, tree)

    def test_intersecting_ranges(self):
        A, B, C, D = Char('a'), Char('b'), Char('c'), Char('d')
        tree = Part(prime=Class(Range(A, C), Range(B, D)))
        clue = Part(
            prime=Expression(
                Alt(Part(prime=A)),
                Alt(Part(prime=B)),
                Alt(Part(prime=C)),
                Alt(Part(prime=D))
            )
        )
        rule = ExpandClassRule()

        node = tree.prime
        rule.visit_Class(node)
        self.assertEqual(tree, clue)

    def test_invalid_range(self):
        B, C = Char('b'), Char('c')
        rng = Range(C, B)
        tree = Part(prime=Class(rng))
        rule = ExpandClassRule()

        node = tree.prime

        with self.assertRaises(TreeTransformerError) as raised_exc:
            rule.visit_Class(node)

        exception = raised_exc.exception
        self.assertEqual(exception.what, Errors.INVALID_RANGE)
        self.assertEqual(exception.nodes, (rng,))


class TestReplaceRepRule(unittest.TestCase):
    def test_apply_repetition_without_end(self):
        E = Char('e')
        tree = Part(prime=E, quant=Repetition(3))
        node = tree.quant
        clue = Part(
            prime=Expression(
                Alt(*repeat(Part(prime=E), 3))
            )
        )
        rule = ReplaceRepRule()

        rule.visit_Repetition(node)
        self.assertEqual(tree, clue)

    def test_apply_repetition_with_end(self):
        E = Char('e')
        tree = Part(prime=E, quant=Repetition(2, 6))
        clue = Part(
            prime=Expression(
                Alt(
                    *repeat(Part(prime=E), 2),
                    Part(prime=Expression(
                        Alt(*repeat(Part(prime=E), 4))
                    ), quant=ZeroOrOne())
                )
            )
        )
        node = tree.quant
        rule = ReplaceRepRule()

        rule.visit_Repetition(node)
        self.assertEqual(tree, clue)

    def test_apply_repetition_invalid_end(self):
        E = Char('e')
        rule = ReplaceRepRule()
        part = Part(prime=E, quant=Repetition(3, 2))
        node = part.quant
        with self.assertRaises(TreeTransformerError) as context:
            rule.visit_Repetition(node)
        self.assertEqual(context.exception.what, Errors.INVALID_REPETITION)


class TestReplaceZeroOrOneRule(unittest.TestCase):
    def test_eliminate(self):
        E = Char('e')
        tree = Part(prime=E, quant=ZeroOrOne())
        node = tree.quant
        clue = Part(
            prime=Expression(
                Alt(Part(prime=E)),
                Alt()
            )
        )

        rule = ReplaceZeroOrOneRule()
        rule.visit_ZeroOrMore(node)

        self.assertEqual(tree, clue)


class TestReplaceOneOrMore(unittest.TestCase):
    def test_replace(self):
        E = Char('e')
        tree = Part(prime=E, quant=OneOrMore())
        node = tree.quant
        clue = Part(
            prime=Expression(
                Alt(
                    Part(prime=E),
                    Part(prime=E, quant=ZeroOrMore())
                )
            )
        )

        rule = ReplaceOneOrMore()
        rule.visit_OneOrMore(node)

        self.assertEqual(tree, clue)

    def test_with_multiple_parts(self):
        Def = Identifier('Definition')
        tree = Expression(
            Alt(
                Part(prime=Identifier('Spacing')),
                Part(prime=Def, quant=OneOrMore()),
                Part(prime=Identifier('EndOfFile'))
            )
        )
        node = tree.alts[0].parts[1].quant
        clue = Expression(
            Alt(
                Part(prime=Identifier('Spacing')),
                Part(prime=Expression(
                    Alt(
                        Part(prime=Def),
                        Part(prime=Def, quant=ZeroOrMore())
                    )
                )),
                Part(prime=Identifier('EndOfFile'))
            )
        )

        rule = ReplaceOneOrMore()
        rule.visit_OneOrMore(node)

        self.assertEqual(tree, clue)


class TestEliminateAndRule(unittest.TestCase):
    def test_rule(self):
        E = Char('e')
        tree = Part(pred=And(), prime=E)
        node = tree.pred
        clue = Part(
            pred=Not,
            prime=Expression(
                Alt(
                    Part(pred=Not(), prime=E)
                )
            )
        )

        rule = EliminateAndRule()
        rule.visit_And(node)

        self.assertTrue(node, clue)


class TestCheckUndefRedefRule(unittest.TestCase):
    def test_undef(self):
        A, B = Identifier('A'), Identifier('B')
        exp = Expression(Alt(Part(prime=B)))
        rule = Rule(A, exp)
        g = Grammar(rule)

        rule = CheckUndefRedefRule()

        rule.visit_Identifier(A)
        rule.visit_Identifier(B)

        with self.assertRaises(TreeTransformerError) as raised_exc:
            rule.exit_Grammar(g)

        exception = raised_exc.exception
        self.assertEqual(exception.what, Errors.UNDEF_RULES)
        self.assertEqual(exception.nodes, (B,))

    def test_redef(self):
        A = Identifier('A')
        exp = Expression(Alt(Part(prime=Char('c'))))
        R = Rule(A, exp)
        g = Grammar(R)

        rule = CheckUndefRedefRule()

        rule.visit_Identifier(A)
        rule.visit_Identifier(A)

        with self.assertRaises(TreeTransformerError) as raised_exc:
            rule.exit_Grammar(g)

        exception = raised_exc.exception
        self.assertEqual(exception.what, Errors.REDEF_RULES)


class TestReplaceNestedExps(unittest.TestCase):
    def test_simple_number_rule(self):
        number_id = Identifier('Number')
        number_gen_id = Identifier('Number_1')

        nested_exp = Expression(Alt(Part(prime=Char('0'))),
                                Alt(Part(prime=Char('1'))))

        # nested_exp should hold initial tree's node as parent,
        # do not copy here
        tree = Grammar(
            Rule(number_id.copy(),
                 Expression(Alt(Part(prime=nested_exp))))
        )

        clue = Grammar(
            Rule(number_id.copy(),
                 Expression(Alt(Part(prime=number_gen_id.copy())))),
            Rule(number_gen_id, nested_exp.copy())
        )

        rule = ReplaceNestedExpsRule()

        node = nested_exp
        rule.visit_Expression(node)

        rule.exit_Grammar(tree)

        self.assertEqual(tree, clue)

    def test_complicated_number_rule(self):
        number_id = Identifier('Number')
        number_gen_id = Identifier('Number_1')

        nested_exp = Expression(Alt(Part(prime=Char('0'))),
                                Alt(Part(prime=Char('1'))))

        nested_exp1 = nested_exp.copy()
        nested_exp2 = nested_exp.copy()

        tree = Grammar(
            Rule(number_id.copy(),
                 Expression(
                     Alt(Part(prime=nested_exp1)),
                     Alt(Part(prime=nested_exp2, quant=ZeroOrMore())))
                 )
        )

        clue = Grammar(
            Rule(number_id.copy(),
                 Expression(
                     Alt(Part(prime=number_gen_id.copy())),
                     Alt(Part(prime=number_gen_id.copy(), quant=ZeroOrMore())))
                 ),
            Rule(number_gen_id, nested_exp.copy())
        )

        rule = ReplaceNestedExpsRule()

        node = nested_exp1
        rule.visit_Expression(node)

        node = nested_exp2
        rule.visit_Expression(node)

        rule.exit_Grammar(tree)

        self.assertEqual(tree, clue)
