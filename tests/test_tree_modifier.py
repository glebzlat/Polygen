import unittest

from polygen.node import (
    DLL,
    Grammar,
    Rule,
    MetaRef,
    MetaRule,
    Expr,
    Alt,
    NamedItem,
    Id,
    String,
    Char,
    AnyChar,
    Class,
    Range,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    And,
    Not,
    Item
)

from polygen.modifier.tree_modifier import TreeModifier
from polygen.modifier.errors import (
    TreeModifierWarning,
    UndefRulesError,
    RedefRulesError,
    UndefEntryError,
    RedefEntryError,
)
from polygen.modifier.modifiers import (
    CheckUndefinedRules,
    CheckRedefinedRules,
    ReplaceNestedExprs,
    FindEntryRule,
    CreateAnyChar,
    # IgnoreRules,  ## TODO: test
    # GenerateMetanames,
    # AssignMetaRules,
    # ValidateNodes
)

from polygen.modifier.leftrec import compute_lr


class TreeModifierTestMeta(type):

    def __init__(cls, name, bases, body):
        if name == "ModifierTest":
            return

        modifier = cls.modifier
        input_data = cls.input_data
        clue = getattr(cls, 'clue', None)
        error = getattr(cls, 'error', None)
        warnings = getattr(cls, 'warnings', [])
        assert clue is not None or error is not None

        if error is not None:
            def test_raises(self: unittest.TestCase):
                vis = TreeModifier([modifier])

                with self.assertRaises(Exception) as context:
                    vis.apply(input_data)

                exc = context.exception
                self.assertEqual(exc, error)

            setattr(cls, 'test_failure', test_raises)

        elif clue is not None:
            def test_success(self: unittest.TestCase):
                vis = TreeModifier([modifier])

                if warnings:
                    with self.assertRaises(TreeModifierWarning) as context:
                        vis.apply(input_data)

                    warn = context.exception
                    warns = warn.args
                    for result_warn, clue_warn in zip(warns, warnings):
                        self.assertEqual(result_warn, clue_warn)

                else:
                    vis.apply(input_data)

                self.assertEqual(input_data, clue)

            setattr(cls, 'test_success', test_success)


bases = (unittest.TestCase,)
ModifierTest = TreeModifierTestMeta("ModifierTest", bases, {})


class Test_CheckUndefinedRules_Success(ModifierTest):
    modifier = CheckUndefinedRules()

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, Id('B'))])])),
        Rule(Id('B'), Expr([Alt([NamedItem(None, AnyChar())])]))
    ])

    clue = input_data


class Test_CheckUndefinedRules_Raises(ModifierTest):
    modifier = CheckUndefinedRules()

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, Id('B'))])]))
    ])

    error = UndefRulesError({Id('B'): [Id('B')]})


class Test_CheckRedefinedRules_Success(ModifierTest):
    modifier = CheckRedefinedRules()

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])]))
    ])

    clue = input_data


class Test_CheckRedefinedRules_Raises(ModifierTest):
    modifier = CheckRedefinedRules()

    rule1 = Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])]))
    rule2 = Rule(Id('A'), Expr([Alt([NamedItem(None, Char('b'))])]))

    input_data = Grammar([rule1, rule2])

    error = RedefRulesError({Id('A'): [rule1, rule2]})


class Test_ReplaceNestedExpr(ModifierTest):
    modifier = ReplaceNestedExprs()

    input_data = Grammar([
        Rule(Id('A'), Expr([
            Alt([NamedItem(None, Expr([
                Alt([NamedItem(None, AnyChar())])
            ]))])
        ]))
    ])

    clue = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, Id('A__GEN_1'))])])),
        Rule(Id('A__GEN_1'), Expr([Alt([NamedItem(None, AnyChar())])]))
    ])


class Test_FindEntryRule_Success(ModifierTest):
    modifier = FindEntryRule()

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])]), entry=True)
    ])

    clue = input_data


class Test_FindEntryRule_Undef(ModifierTest):
    modifier = FindEntryRule()

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])]))
    ])

    error = UndefEntryError(None)


class Test_FindEntryRule_Redef(ModifierTest):
    modifier = FindEntryRule()

    rule1 = Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])]), entry=True)
    rule2 = Rule(Id('B'), Expr([Alt([NamedItem(None, AnyChar())])]), entry=True)

    input_data = Grammar([rule1, rule2])

    error = RedefEntryError([rule1, rule2])


class Test_CreateAnyChar_non_strict(ModifierTest):
    modifier = CreateAnyChar()

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])]))
    ])

    clue = input_data


class Test_CreateAnyChar_strict(ModifierTest):
    # Modifier collects characters from the grammar and creates
    # artificial rule, which matches only characters that was found and
    # nothing else

    modifier = CreateAnyChar(strict=True)

    input_data = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, AnyChar())])])),
        Rule(Id('B'), Expr([
            Alt([NamedItem(
                None,
                String([Char('a'), Char('b'), Char('c')]))])]))
    ])

    clue = Grammar([
        Rule(Id('A'), Expr([Alt([NamedItem(None, Id('AnyChar__GEN'))])])),
        Rule(Id('B'), Expr([
            Alt([NamedItem(
                None,
                String([Char('a'), Char('b'), Char('c')]))])])),
        Rule(Id('AnyChar__GEN'), Expr([
            Alt([NamedItem(
                None,
                Class([Range(Char('a'), Char('c'))]))])]))
    ])


class Test_compute_lr(unittest.TestCase):

    def test_simple_lr(self):
        rule = Rule(Id('A'), Expr([Alt([NamedItem(None, Id('A'))])]))
        tree = Grammar([rule])
        tree.entry = rule

        compute_lr(tree)

        self.assertTrue(rule.leftrec)

    def test_simple_nullable(self):
        nullable_rule = Rule(
            Id('A'), Expr([Alt([NamedItem(None, ZeroOrOne(Char('.')))])]))
        rule = Rule(
            Id('B'), Expr([Alt([NamedItem(None, Id('A')),
                                NamedItem(None, Id('B'))])]))
        tree = Grammar([nullable_rule, rule])
        tree.entry = rule

        compute_lr(tree)

        self.assertTrue(rule.leftrec)

    def test_complex_nullable(self):
        nullable_rule = Rule(
            Id('A'),
            Expr([
                Alt([NamedItem(None, Char('='))]),
                Alt([NamedItem(None, ZeroOrOne(Char('-')))])]))
        rule = Rule(
            Id('B'), Expr([Alt([NamedItem(None, Id('A')),
                                NamedItem(None, Id('B'))])]))
        tree = Grammar([nullable_rule, rule])
        tree.entry = rule

        compute_lr(tree)

        self.assertTrue(rule.leftrec)

    def test_nullable_rule_after_rhs_id(self):
        nullable_rule = Rule(
            Id('A'),
            Expr([
                Alt([NamedItem(None, Char('='))]),
                Alt([NamedItem(None, ZeroOrOne(Char('-')))])]))
        rule = Rule(
            Id('B'), Expr([Alt([NamedItem(None, Id('A')),
                                NamedItem(None, Id('B'))])]))
        tree = Grammar([rule, nullable_rule])
        tree.entry = rule

        compute_lr(tree)

        self.assertTrue(rule.leftrec)
