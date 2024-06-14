import unittest

from polygen.parser import Parser
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


class ParserTestMetaclass(type):
    def __init__(cls, name, bases, body):
        if name == 'ParserTest':
            return

        node_extractor = getattr(cls, 'node_extractor', lambda obj: obj)

        def test_successes(self):
            for input, clue in self.successes:
                parser = Parser(input)
                result = parser.parse()
                self.assertIsNotNone(result)

                value = node_extractor(result.value)
                self.assertEqual(value, clue)

        def test_failures(self):
            for input in self.failures:
                parser = Parser(input)
                result = parser.parse()
                self.assertIsNone(result)

        if getattr(cls, 'successes', None):
            setattr(cls, 'test_successes', test_successes)
        if getattr(cls, 'failures', None):
            setattr(cls, 'test_failures', test_failures)


bases = (unittest.TestCase,)
ParserTest = ParserTestMetaclass('ParserTest', bases, {})


class TestSimpleRule(ParserTest):
    successes = [
        ("Id <- ", Grammar([Rule(Id('Id'), Expr([Alt([])]))])),
        ("A <- B", Grammar([
            Rule(Id('A'), Expr([Alt([NamedItem(None, Id('B'))])]))])),
        ("A\t\n\t\r<-  \n\rB", Grammar([
            Rule(Id('A'), Expr([Alt([NamedItem(None, Id('B'))])]))])),
        ("A <- (B)", Grammar([
            Rule(Id('A'), Expr([Alt([
                NamedItem(None, Expr([Alt([NamedItem(None, Id('B'))])]))
            ])]))])),
    ]

    failures = [
        "",
        "Id <- <-",
        "<- Expr",
        "Id < - Expr",
        "Id Expr",
        "(Id) <- Expr",
        "Id <- Expr)",
        "Id <- (Expr",
        "3d <- Expr",
        "Id <- 23expr",
        "1d <- Expr"
    ]


class TestRuleMetaRef(ParserTest):
    metaref = MetaRef(Id('name'))

    successes = [
        ("Id <- Expr $name", Grammar([
            Rule(Id('Id'), Expr([
                Alt([
                    NamedItem(None, Id('Expr'))
                ], metarule=metaref)
            ]))
        ]))
    ]

    failures = [
        "Id <- Expr $",
        "Id <- Expr $ Foo <- Bar"
    ]


class TestRuleMetaRule(ParserTest):
    metarule1 = MetaRule(None, expr="hello world")
    metarule2 = MetaRule(None, expr="{nested}")

    successes = [
        ("A <- B ${hello world}", Grammar([
            Rule(Id('A'), Expr([
                Alt([NamedItem(None, Id('B'))], metarule=metarule1)
            ]))
        ])),
        ("A <- B ${{nested}}", Grammar([
            Rule(Id('A'), Expr([
                Alt([NamedItem(None, Id('B'))], metarule=metarule2)
            ]))
        ])),
        ("A <- B $name {expr}", Grammar([
            Rule(Id('A'), Expr([
                Alt([NamedItem(None, Id('B'))])
            ]))
        ], [
            MetaRule(Id('name'), 'expr')
        ]))
    ]

    failures = [
        "Id <- Expr ${invalid}}",
        "Id <- Expr ${{invalid}",
        "Id <- Expr $ {invalid}"
        "Id <- Expr ${",
        "Id <- Expr }",
    ]


class TestEntryRule(ParserTest):
    successes = [
        ("@entry\nA <- B", Grammar([
            Rule(Id('A'), Expr([
                Alt([NamedItem(None, Id('B'))])
            ]), entry=False)
        ]))
    ]


class TestRuleDirectives(unittest.TestCase):
    def test_entry(self):
        parser = Parser("@entry A <- B")
        result = parser.parse()

        self.assertIsNotNone(result)
        self.assertTrue(result.value.rules.begin.entry)
        self.assertFalse(result.value.rules.begin.ignore)

    def test_ignore(self):
        parser = Parser("@ignore A <- B")
        result = parser.parse()

        self.assertIsNotNone(result)
        self.assertTrue(result.value.rules.begin.ignore)


class TestMetaRule(ParserTest):
    def test_1(self):
        parser = Parser("$name {expr}")
        result = parser.parse()

        self.assertIsNotNone(result)

        rule = result.value.metarules.begin
        self.assertEqual(rule.id, Id('name'))
        self.assertEqual(rule.expr, 'expr')

    failures = [
        "metadef {hello world}",
        "${hello world}"
    ]


class TestCharAndString(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar) -> Item:
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- 'c'", Char('c')),
        ("A <- 'abc'", String([Char('a'), Char('b'), Char('c')])),
        ('A <- "c"', Char('c')),
        ('A <- "abc"', String([Char('a'), Char('b'), Char('c')])),

        ("A <- '\\''", Char('\'')),
        ('A <- "\\""', Char('"')),
        ("A <- '\\n'", Char('\n')),
        ("A <- '\\r'", Char('\r')),
        ("A <- '\\t'", Char('\t')),
        ("A <- '\\['", Char('[')),
        ("A <- '\\]'", Char(']')),
        ("A <- '\\\\'", Char('\\')),

        ("A <- '['", Char('[')),
        ("A <- ']'", Char(']')),

        ("A <- '\\141'", Char(0o141)),
        ("A <- '\\73'", Char(0o73)),

        ("A <- '\\u03c0'", Char(0x03c0)),
        ("A <- '\\uabcd'", Char(0xabcd)),
        ("A <- '\\uABCD'", Char(0xabcd))
    ]

    failures = [
        "Id <- '",
        'Id <- "',

        "Id <- '\\a'",
        "Id <- '\\b'",

        "Id <- '\\u03c'",
        "Id <- '\\u 03c0'",
        "Id <- '\\u12g3'"
    ]


class TestRepetition(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- B{1}", Repetition(Id('B'), 1, None)),
        ("A <- B{123}", Repetition(Id('B'), 123, None)),
        ("A <- B{1,2}", Repetition(Id('B'), 1, 2))
    ]

    failures = [
        "Id <- E{}",
        "Id <- E{1,}",
        "Id <- E{a}",
        "Id <- E{,2}",
        "Id <- E{,}"
    ]


class TestAnyChar(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return list(DLL.astuple(gram.rules.begin.expr.alts.begin.items))

    successes = [
        ("Id <- .", [NamedItem(None, AnyChar())]),
        ("Id <- ...", [NamedItem(None, AnyChar()),
                       NamedItem(None, AnyChar()),
                       NamedItem(None, AnyChar())])
    ]


class TestZeroOrOne(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- B?", ZeroOrOne(Id('B')))
    ]

    failures = [
        "A <- ?"
    ]


class TestZeroOrMore(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- B*", ZeroOrMore(Id('B')))
    ]

    failures = [
        "A <- *"
    ]


class TestOneOrMore(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- B+", OneOrMore(Id('B')))
    ]

    failures = [
        "A <- +"
    ]


class TestAnd(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- &B", And(Id('B'))),
        ("A <- &(B)", And(Expr([Alt([NamedItem(None, Id('B'))])]))),
        ("A <- &B?", And(ZeroOrOne(Id('B')))),
    ]

    failures = [
        "A <- &&B",
        "A <- &!B",
        "A <- &!",
        "A <- &?"
    ]


class TestNot(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- !B", Not(Id('B'))),
        ("A <- !(B)", Not(Expr([Alt([NamedItem(None, Id('B'))])]))),
        ("A <- !B?", Not(ZeroOrOne(Id('B')))),
    ]

    failures = [
        "A <- !!B",
        "A <- &!B",
        "A <- &!",
        "A <- !&B",
        "A <- !?"
    ]


class TestClass(ParserTest):

    @staticmethod
    def node_extractor(gram: Grammar):
        return gram.rules.begin.expr.alts.begin.items.begin.item

    successes = [
        ("A <- []", Class([])),
        ("A <- [a]", Class([Range(Char('a'))])),
        ("A <- [ab]", Class([Range(Char('a')), Range(Char('b'))])),
        ("A <- [a-c]", Class([Range(Char('a'), Char('c'))])),
        ("A <- [a-c0-9]", Class([Range(Char('a'), Char('c')),
                                 Range(Char('0'), Char('9'))])),
        ("A <- [---]", Class([Range(Char('-'), Char('-'))])),
        ("A <- [a-z-]", Class([Range(Char('a'), Char('z')), Range(Char('-'))])),
        ("A <- [-a-z-]", Class([Range(Char('-')),
                                Range(Char('a'), Char('z')),
                                Range(Char('-'))]))
    ]
