import unittest

from polygen.translator import Context
from polygen.passes.check_undef_rules import CheckUndefRules, UndefRuleError
from polygen.node import Grammar, Rule, Id, Expr, Alt, NamedItem, AnyChar


class TestCheckUndefRules(unittest.TestCase):

    # def test_success(self):
    #     gram = Grammar([
    #         Rule(Id('A'), Expr([Alt([NamedItem(None, Id('B'))])])),
    #         Rule(Id('B'), Expr([Alt([NamedItem(None, AnyChar())])]))
    #     ])
    #
    #     ctx = Context()
    #     ctx.grammar = gram
    #     p = CheckUndefRules()
    #     p.translate(ctx)

    def test_raises(self):
        id = Id('B')
        rule = Rule(Id('A'), Expr([Alt([NamedItem(None, id)])]))
        gram = Grammar([rule])

        ctx = Context()
        ctx.grammar = gram
        p = CheckUndefRules()

        p.translate(ctx)

        errors = ctx.errors
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[-1], UndefRuleError)
        self.assertEqual(errors[-1].args, (id,))
