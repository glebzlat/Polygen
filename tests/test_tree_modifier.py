import unittest

from polygen.grammar.node import (
    Grammar,
    Rule,
    MetaRule,
    MetaRef,
    Identifier,
    Expression,
    Alt,
    Part,
    Char,
    AnyChar,
    String,
    Range,
    Class,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    Optional,
    And,
    Not,
)

from polygen.grammar.tree_modifier import (
    TreeModifierError,
    TreeModifierWarning,
    InvalidRangeError,
    InvalidRepetitionError,
    UndefRulesError,
    RedefRulesError,
    RedefEntryError,
    EntryNotDefinedError,
    RedefMetaRulesError,
    UndefMetaRefsError,
    MetanameRedefError,
    UnusedMetaRuleWarning,
    LookaheadMetanameWarning,
    ExpandClass,
    ReplaceRep,
    CheckUndefRedef,
    SimplifyNestedExps,
    ReplaceNestedExps,
    CreateAnyCharRule,
    FindEntryRule,
    IgnoreRules,
    GenerateMetanames,
    SubstituteMetaRefs,
    TreeModifier
)


class TreeModifierTestMetaClass(type):
    def __init__(cls, name, bases, body):
        if name == 'TreeModifierTest':
            return

        modifier_cls = cls.modifier
        args = getattr(cls, 'args', None) or []
        kwargs = getattr(cls, 'kwargs', None) or {}

        input_data = cls.input_data
        clue = getattr(cls, 'clue', None)
        error = getattr(cls, 'error', None)
        warnings = getattr(cls, 'warnings', [])
        assert clue is not None or error is not None

        inspect_result = getattr(cls, 'inspect_result', None)

        if error is not None:
            def test_raises(self):
                modifier = modifier_cls(*args, **kwargs)
                tree_visitor = TreeModifier([[modifier]])
                result = input_data.copy()

                exc_args = error
                with self.assertRaises(TreeModifierError) as context:
                    tree_visitor.visit(result)

                exception = context.exception
                for semantic_err, clue_exc in zip(exception.args, exc_args):
                    self.assertEqual(semantic_err, clue_exc)

            setattr(cls, 'test_raises', test_raises)

        elif clue is not None:
            def test_success(self):
                modifier = modifier_cls(*args, **kwargs)
                tree_visitor = TreeModifier([[modifier]])
                result = input_data.copy(deep=True)

                if warnings:
                    with self.assertRaises(TreeModifierWarning) as context:
                        tree_visitor.visit(result)

                    warn = context.exception
                    sem_warns = warn.args
                    for result_warn, clue_warn in zip(sem_warns, warnings):
                        self.assertEqual(result_warn, clue_warn)

                else:
                    tree_visitor.visit(result)

                if inspect_result:
                    inspect_result(self, result)
                self.assertEqual(result, clue)

            setattr(cls, 'test_success', test_success)


bases = (unittest.TestCase,)
TreeModifierTest = TreeModifierTestMetaClass('TreeModifierTest', bases, {})


class ExpandClass_SimpleTest(TreeModifierTest):
    modifier = ExpandClass

    A, B, C = Char('a'), Char('b'), Char('c')
    AltA, AltB, AltC = (Alt(Part(prime=i)) for i in (A, B, C))

    input_data = Part(Class(Range(A, C)))
    clue = Part(Expression(AltA, AltB, AltC))


class ExpandClass_ComplicatedCase(TreeModifierTest):
    modifier = ExpandClass

    A, B, C, _1, _2, _3 = (Char(i) for i in ('a', 'b', 'c', '1', '2', '3'))
    AltA, AltB, AltC, Alt1, Alt2, Alt3 = (
        Alt(Part(prime=i)) for i in (A, B, C, _1, _2, _3))

    input_data = Part(Class(Range(A, C), Range(_1, _3)))
    clue = Part(Expression(Alt1, Alt2, Alt3, AltA, AltB, AltC))


class ExpandClass_InvalidRange(TreeModifierTest):
    modifier = ExpandClass

    A, B, C = Char('a'), Char('b'), Char('c')
    Rng = Range(C, A)

    input_data = Part(Class(Rng))
    error = (InvalidRangeError(Range(Char("c"), Char("a"))),)


class ReplaceRep_SimpleTest(TreeModifierTest):
    modifier = ReplaceRep

    E = Char('e')

    input_data = Part(prime=E, quant=Repetition(2))
    clue = Part(Expression(Alt(Part(prime=E), Part(prime=E))))


class ReplaceRep_TwoBounds(TreeModifierTest):
    modifier = ReplaceRep

    E = Char('e')

    input_data = Part(prime=E, quant=Repetition(2, 4))
    clue = Part(Expression(
        Alt(Part(prime=E),
            Part(prime=E),
            Part(prime=E, quant=ZeroOrOne()),
            Part(prime=E, quant=ZeroOrOne()))))


class ReplaceRep_InvalidRep(TreeModifierTest):
    modifier = ReplaceRep

    E = Char('e')
    Rep = Repetition(3, 2)

    input_data = Part(prime=E, quant=Rep)
    error = (InvalidRepetitionError(Rep),)


class CheckUndefRedef_RedefTest(TreeModifierTest):
    modifier = CheckUndefRedef

    Id = Identifier('A')
    RuleA = Rule(Id, Expression())

    input_data = Grammar(RuleA, RuleA)
    error = (RedefRulesError({Id: [RuleA, RuleA]}),)


class CheckUndefRedef_UndefTest(TreeModifierTest):
    modifier = CheckUndefRedef

    input_data = Grammar(
        Rule(Identifier('A'), Expression(Alt(Part(prime=Identifier('B'))))))
    error = (UndefRulesError({Identifier('B'): Rule(
        Identifier('A'),
        Expression(Alt(Part(prime=Identifier('B')))))}),)


class CheckUndefRedef_NoExc(TreeModifierTest):
    modifier = CheckUndefRedef

    input_data = Grammar(
        Rule(Identifier('A'), Expression(Alt(Part(prime=Identifier('A'))))),
        Rule(Identifier('B'), Expression(Alt(Part(prime=Char('C'))))))
    clue = input_data


class SimplifyNestedExps_SimpleTest(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(prime=Nested)))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Nested)


class SimplifyNestedExps_NoEffect(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Exp = Expression(Alt(Part(prime=Char('A'))))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Exp)


class SimplifyNestedExps_OmitZeroOrOne(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(prime=Nested, quant=ZeroOrOne())))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Exp)


class SimplifyNestedExps_OmitZeroOrMore(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(prime=Nested, quant=ZeroOrMore())))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Exp)


class SimplifyNestedExps_OmitOneOrMore(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(prime=Nested, quant=OneOrMore())))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Exp)


class SimplifyNestedExps_OmitAnd(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(lookahead=And(), prime=Nested)))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Exp)


class SimplifyNestedExps_OmitNot(TreeModifierTest):
    modifier = SimplifyNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(lookahead=Not(), prime=Nested)))

    input_data = Rule(Id, Exp)
    clue = Rule(Id, Exp)


class ReplaceNestedExps_SimpleTest(TreeModifierTest):
    modifier = ReplaceNestedExps

    Id = Identifier('R')
    Nested = Expression(Alt(Part(prime=Char('A'))))
    Exp = Expression(Alt(Part(prime=Nested)))

    GenId = Identifier('R__GEN_1')
    NewExp = Expression(Alt(Part(prime=GenId)))

    input_data = Grammar(Rule(Id, Exp))
    clue = Grammar(Rule(Id, NewExp), Rule(GenId, Nested))


class ReplaceNestedExps_DeepNesting(TreeModifierTest):
    modifier = ReplaceNestedExps

    Id = Identifier('R')
    Nested2 = Expression(Alt(Part(prime=Char('A'))))
    Nested1 = Expression(Alt(Part(prime=Nested2)))
    Exp = Expression(Alt(Part(prime=Nested1)))

    GenId1 = Identifier('R__GEN_1')
    GenId2 = Identifier('R__GEN_2')
    NewExp = Expression(Alt(Part(prime=GenId2)))
    NewNested1 = Expression(Alt(Part(prime=GenId1)))

    input_data = Grammar(Rule(Id, Exp))
    clue = Grammar(
        Rule(Id, NewExp),
        Rule(GenId1, Nested2),
        Rule(GenId2, NewNested1))


class ReplaceNestedExps_NoEffect(TreeModifierTest):
    modifier = ReplaceNestedExps

    input_data = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('A'))))))
    clue = input_data


class CreateAnyCharRule_NoAnyChar(TreeModifierTest):
    modifier = CreateAnyCharRule

    input_data = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('A'))))))
    clue = input_data


class CreateAnyCharRule_SimpleTest(TreeModifierTest):
    modifier = CreateAnyCharRule

    Id = Identifier('R')
    AnyCharId = Identifier('AnyChar__GEN')

    input_data = Grammar(
        Rule(Id, Expression(Alt(Part(prime=AnyChar())))))
    clue = Grammar(
        Rule(Id, Expression(Alt(Part(prime=AnyCharId)))),
        Rule(AnyCharId, Expression(Alt(Part(prime=AnyChar())))))


class FindEntryRule_Valid(TreeModifierTest):
    modifier = FindEntryRule

    input_data = Grammar(
        Rule(Identifier('R'),
             Expression(Alt(Part(prime=Char('A')))),
             directives=['entry']))
    clue = input_data


class FindEntryRule_NotFound(TreeModifierTest):
    modifier = FindEntryRule

    input_data = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('A'))))))
    error = (EntryNotDefinedError(),)


class FindEntryRule_Redef(TreeModifierTest):
    modifier = FindEntryRule

    Redef = Rule(Identifier('B'),
                 Expression(Alt()),
                 directives=['entry'])

    input_data = Grammar(
        Rule(Identifier('A'),
             Expression(Alt()),
             directives=['entry']),
        Redef)
    error = (RedefEntryError(Redef),)


class IgnoreRules_SimpleTest(TreeModifierTest):
    modifier = IgnoreRules

    input_data = Grammar(
        Rule(Identifier('A'), Expression(Alt(Part(prime=Identifier('B'))))),
        Rule(Identifier('B'), Expression(Alt()), directives=['ignore']))
    clue = Grammar(
        Rule(Identifier('A'), Expression(Alt(Part(prime=Identifier('B'),
                                                  metaname='_')))),
        Rule(Identifier('B'), Expression(Alt()), directives=['ignore']))

    def inspect_result(self, node: Grammar):
        rule = node.get(Identifier('A'))
        self.assertIsNotNone(rule)
        self.assertEqual(rule.expr.alts[0].parts[0].metaname, '_')


class IgnoreRules_MultipleRules(TreeModifierTest):
    modifier = IgnoreRules

    input_data = Grammar(
        Rule(Identifier('A'), Expression(Alt(Part(prime=Identifier('C'))))),
        Rule(Identifier('B'), Expression(Alt(Part(prime=Identifier('C'))))),
        Rule(Identifier('C'), Expression(Alt()), directives=['ignore']),
        Rule(Identifier('D'), Expression(Alt(Part(prime=Identifier('A'))))))
    clue = Grammar(
        Rule(Identifier('A'), Expression(Alt(Part(prime=Identifier('C'),
                                                  metaname='_')))),
        Rule(Identifier('B'), Expression(Alt(Part(prime=Identifier('C'),
                                                  metaname='_')))),
        Rule(Identifier('C'), Expression(Alt()), directives=['ignore']),
        Rule(Identifier('D'), Expression(Alt(Part(prime=Identifier('A'))))))

    def inspect_result(self, node: Grammar):
        rule = node.get(Identifier('A'))
        self.assertIsNotNone(rule)
        self.assertEqual(rule.expr.alts[0].parts[0].metaname, '_')

        rule = node.get(Identifier('B'))
        self.assertIsNotNone(rule)
        self.assertEqual(rule.expr.alts[0].parts[0].metaname, '_')

        rule = node.get(Identifier('D'))
        self.assertIsNotNone(rule)
        self.assertIsNone(rule.expr.alts[0].parts[0].metaname)


class GenerateMetanames_Identifier(TreeModifierTest):
    modifier = GenerateMetanames

    input_data = Alt(Part(prime=Identifier('Id')))
    clue = Alt(Part(prime=Identifier('Id'), metaname='id'))


class GenerateMetanames_Indexed(TreeModifierTest):
    modifier = GenerateMetanames

    input_data = Alt(
        Part(prime=Char('a')),
        Part(prime=String(Char('a'), Char('b'))))
    clue = Alt(
        Part(prime=Char('a'), metaname='_1'),
        Part(prime=String(Char('a'), Char('b')), metaname='_2'))


class GenerateMetanames_Lookahead(TreeModifierTest):
    modifier = GenerateMetanames

    input_data = Alt(
        Part(lookahead=And(), prime=Identifier('A')),
        Part(lookahead=Not(), prime=Identifier('B')))
    clue = Alt(
        Part(lookahead=And(), prime=Identifier('A'), metaname='_'),
        Part(lookahead=Not(), prime=Identifier('B'), metaname='_'))


class GenerateMetanames_Redef(TreeModifierTest):
    modifier = GenerateMetanames

    Metaname = 'myvar'
    Part1 = Part(prime=Identifier('A'), metaname=Metaname)
    Part2 = Part(prime=Char('B'), metaname=Metaname)

    input_data = Alt(Part1, Part2)
    error = [MetanameRedefError(Part2)]


class GenerateMetanames_IdenticalIds(TreeModifierTest):
    modifier = GenerateMetanames

    input_data = Alt(
        Part(prime=Identifier('A')),
        Part(prime=Identifier('A')))
    clue = Alt(
        Part(prime=Identifier('A'), metaname='a'),
        Part(prime=Identifier('A'), metaname='a1'))


class GenerateMetanames_PredefName(TreeModifierTest):
    modifier = GenerateMetanames

    input_data = Alt(
        Part(prime=Identifier('A'), metaname='hello'),
        Part(prime=Identifier('A'), metaname='world'))
    clue = Alt(
        Part(prime=Identifier('A'), metaname='hello'),
        Part(prime=Identifier('A'), metaname='world'))


class GenerateMetanames_LookaheadName(TreeModifierTest):
    modifier = GenerateMetanames

    Meta = Part(lookahead=And(), prime=Identifier('A'), metaname='a')

    input_data = Alt(
        Meta,
        Part(lookahead=Not(), prime=Identifier('B')))
    clue = Alt(
        Part(lookahead=And(), prime=Identifier('A'), metaname='_'),
        Part(lookahead=Not(), prime=Identifier('B'), metaname='_'))

    warnings = [LookaheadMetanameWarning(Meta)]


class SubstituteMetaRefs_Success(TreeModifierTest):
    modifier = SubstituteMetaRefs

    MetaId = Identifier('M')
    MetaBody = 'hello world'
    Meta = MetaRule(id=MetaId, expr=MetaBody)

    input_data = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('E')),
                                             metarule=MetaRef(MetaId)))),
        Meta)
    clue = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('E')),
                                             metarule=Meta))))

    def inspect_result(self, node: Grammar):
        rule = node.get(Identifier('R'))
        self.assertIsNotNone(rule)
        self.assertEqual(rule.expr.alts[0].metarule, self.Meta)


class SubstituteMetaRefs_UnusedMeta(TreeModifierTest):
    modifier = SubstituteMetaRefs

    MetaId = Identifier('M')
    MetaBody = 'hello world'
    Meta = MetaRule(id=MetaId, expr=MetaBody)

    input_data = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('E'))))),
        Meta)
    clue = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('E'))))))

    warnings = [UnusedMetaRuleWarning(Meta)]


class SubstituteMetaRefs_RedefMeta(TreeModifierTest):
    modifier = SubstituteMetaRefs

    MetaId = Identifier('M')
    MetaBody = 'hello world'
    Meta1 = MetaRule(id=MetaId, expr=MetaBody)
    Meta2 = MetaRule(id=MetaId, expr=MetaBody)

    input_data = Grammar(
        Rule(Identifier('R'), Expression(Alt(Part(prime=Char('E'))))),
        Meta1, Meta2)
    error = (RedefMetaRulesError({Identifier('M'): [Meta1, Meta2]}),)


class SubstituteMetaRefs_UndefMeta(TreeModifierTest):
    modifier = SubstituteMetaRefs

    MetaId = Identifier('M')
    MetaBody = 'hello world'
    Meta = MetaRule(id=MetaId, expr=MetaBody)
    A = Alt(Part(prime=Char('E')), metarule=MetaRef(MetaId))

    input_data = Grammar(
        Rule(Identifier('R'), Expression(A)))
    error = (UndefMetaRefsError({Identifier('M'): [A]}),)
