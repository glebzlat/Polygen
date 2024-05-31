import unittest

from polygen.parser import Parser
from polygen.node import (
    Grammar,
    Expression,
    Rule,
    MetaRef,
    MetaRule,
    Identifier,
    Range,
    Alt,
    Part,
    AnyChar,
    String,
    Class,
    Not,
    And,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    Char
)


class ParserTestMetaclass(type):
    def __init__(cls, name, bases, body):
        if name == 'ParserTest':
            return

        def test_successes(self):
            for input, clue in self.successes:
                parser = Parser(input)
                result = parser.parse()
                self.assertEqual(result, clue)

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
        ("Id <- ", Grammar(Rule(Identifier('Id'), Expression(Alt())))),
        ("Id <- Id", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Id'))))))),
        ("Id <- Expr", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr'))))))),
        ("Id1 <- Id2 <-", Grammar(
            Rule(Identifier('Id1'), Expression(Alt())),
            Rule(Identifier('Id2'), Expression(Alt())))),
        ("Id\t\n\t\r<-      \n\rExpr\t\r", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr'))))))),
        ("Id <- (Expr)", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Expression(Alt(
                              Part(metaname=None,
                                   prime=Identifier('Expr')))))))))),
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
        "Id <- 23expr"
    ]


class TestRuleMetaRef(ParserTest):
    metaref = MetaRef(Identifier('rulename'))
    successes = [
        ("Id <- Expr $rulename", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')),
                     metarule=metaref))))),
        ("Id <- Expr $\t\nrulename", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')),
                     metarule=metaref)))))
    ]

    failures = [
        "Id <- Expr $",
        "Id <- Expr $ Foo <- Bar"
    ]


class TestRuleMetaRule(ParserTest):
    metarule1 = MetaRule(id=None, expr="hello world")
    metarule2 = MetaRule(id=None, expr="{{{properly nested}}}")
    metarule3 = MetaRule(id=None, expr="\n\t\r hello world\n\r ")

    successes = [
        ("Id <- Expr ${hello world}", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')),
                     metarule=metarule1))))),
        ("Id <- Expr ${{{{properly nested}}}}", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')),
                     metarule=metarule2))))),
        ("Id <- Expr ${\n\t\r hello world\n\r }", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')),
                     metarule=metarule3))))),
        ("Id <- Expr $rulename {hello world}", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('Expr'))))),
            MetaRule(id=Identifier('rulename'), expr='hello world')))
    ]

    failures = [
        "Id <- Expr ${invalid}}",
        "Id <- Expr ${{invalid}",
        "Id <- Expr $ {invalid}"
        "Id <- Expr ${",
        "Id <- Expr }",
    ]


class TestRuleDirective(ParserTest):

    # TODO: add Rule directives into comparison
    successes = [
        ("@directive\nId <- Expr", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')))),
                 directives=["directive"]))),
        ("@ a @b Id <- Expr", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Identifier('Expr')))),
                 directives=["a", "b"])))
    ]

    failures = [
        "@ Id <- Expr",
        "@Id <- Expr"
    ]


class TestMetaDef(ParserTest):
    successes = [
        ("$metadef {hello world}", Grammar(
            MetaRule(id=Identifier('metadef'), expr='hello world'))),
        ("$ metadef{hello world}", Grammar(
            MetaRule(id=Identifier('metadef'), expr='hello world'))),
    ]

    failures = [
        "metadef {hello world}",
        "${hello world}"
    ]


class TestCharString(ParserTest):
    successes = [
        ("Id <- 'c'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('c'))))))),
        ("Id <- 'str'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=String(Char('s'), Char('t'), Char('r')))))))),
        ('Id <- "c"', Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('c'))))))),
        ('Id <- "str"', Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=String(Char('s'), Char('t'), Char('r')))))))),
        ("Id <- '\\''", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('\''))))))),
        ('Id <- "\\""', Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('"'))))))),
        ("Id <- '\\n'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('\n'))))))),

        # XXX: maybe this is incorrect
        ("Id <- '\n'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('\n'))))))),

        ("Id <- '\\r'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('\r'))))))),
        ("Id <- '\\t'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('\t'))))))),
        ("Id <- '\\['", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('['))))))),
        ("Id <- '\\]'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(']'))))))),
        ("Id <- '\\\\'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char('\\'))))))),
        ("Id <- '\\141'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0o141))))))),
        ("Id <- '\\73'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0o73))))))),
    ]

    failures = [
        "Id <- '",
        'Id <- "',
        "Id <- '\\a'",
        "Id <- '\\b'",
    ]


class TestUnicodeChar(ParserTest):
    successes = [
        ("Id <- '\\u03C0'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0x03c0))))))),
        ("Id <- '\\u03c0'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0x03c0))))))),
        ("Id <- '\\uabcd'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0xabcd))))))),
        ("Id <- '\\ufeed'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0xfeed))))))),
        ("Id <- '\\uFEED'", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Char(0xFEED))))))),
    ]

    failures = [
        "Id <- '\\u03c'",
        "Id <- '\\u 03c0'",
        "Id <- '\\u12g3'"
    ]


class TestRepetition(ParserTest):
    successes = [
        ("Id <- E{1}", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('E'),
                          quant=Repetition(1))))))),
        ("Id <- E{123}", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('E'),
                          quant=Repetition(123))))))),
        ("Id <- E{1,2}", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('E'),
                          quant=Repetition(1, 2)))))))
    ]

    failures = [
        "Id <- E{}",
        "Id <- E{1,}",
        "Id <- E{a}",
        "Id <- E{,2}",
        "Id <- E{,}"
    ]


class TestAnyChar(ParserTest):
    successes = [
        ("Id <- .", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=AnyChar())))))),
        ("Id <- ...", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=AnyChar()),
                     Part(metaname=None,
                          prime=AnyChar()),
                     Part(metaname=None,
                          prime=AnyChar()))))))
    ]


class TestZeroOrOne(ParserTest):
    successes = [
        ("Id <- E?", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('E'),
                          quant=ZeroOrOne())))))),
        ("Id <- .?", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=AnyChar(),
                          quant=ZeroOrOne()))))))
    ]

    failures = [
        "Id <- ?"
    ]


class TestZeroOrMore(ParserTest):
    successes = [
        ("Id <- E*", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('E'),
                          quant=ZeroOrMore())))))),
        ("Id <- .*", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=AnyChar(),
                          quant=ZeroOrMore()))))))
    ]

    failures = [
        "Id <- *"
    ]


class TestOneOrMore(ParserTest):
    successes = [
        ("Id <- E+", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Identifier('E'),
                          quant=OneOrMore())))))),
        ("Id <- .+", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=AnyChar(),
                          quant=OneOrMore()))))))
    ]

    failures = [
        "Id <- +"
    ]


class TestAnd(ParserTest):
    successes = [
        ("Id <- &E", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          lookahead=And(),
                          prime=Identifier('E'))))))),
        ("Id <- &E?", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          lookahead=And(),
                          prime=Identifier('E'),
                          quant=ZeroOrOne())))))),
        ("Id <- &A B", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          lookahead=And(),
                          prime=Identifier('A')),
                     Part(metaname=None,
                          prime=Identifier('B'))))))),
    ]

    failures = [
        "Id <- &&E",
        "Id <- &",
        "Id <- &?",
        "Id <- &*",
        "Id <- &+"
    ]


class TestNot(ParserTest):
    successes = [
        ("Id <- !E", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          lookahead=Not(),
                          prime=Identifier('E'))))))),
        ("Id <- !E?", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          lookahead=Not(),
                          prime=Identifier('E'),
                          quant=ZeroOrOne())))))),
        ("Id <- !A B", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          lookahead=Not(),
                          prime=Identifier('A')),
                     Part(metaname=None,
                          prime=Identifier('B'))))))),
    ]

    failures = [
        "Id <- !!E",
        "Id <- !",
        "Id <- !?",
        "Id <- !*",
        "Id <- !+"
    ]


class TestClass(ParserTest):
    successes = [
        ("Id <- []", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(Part(metaname=None, prime=Class())))))),
        ("Id <- [a]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Class(Range(Char('a'))))))))),
        ("Id <- [\\]]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Class(Range(Char(']'))))))))),
        ("Id <- [\\[]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Class(Range(Char('['))))))))),
        ("Id <- [-]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None, prime=Class(Range(Char('-'))))))))),
        ("Id <- [abc]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Class(
                              Range(Char('a')),
                              Range(Char('b')),
                              Range(Char('c'))))))))),
        ("Id <- [a-c]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Class(Range(Char('a'), Char('c'))))))))),
        ("Id <- [---]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Class(Range(Char('-'), Char('-'))))))))),
        ("Id <- [a-z0-9]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Class(
                              Range(Char('a'), Char('z')),
                              Range(Char('0'), Char('9'))))))))),
        ("Id <- [a-z-]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Class(
                              Range(Char('a'), Char('z')),
                              Range(Char('-'))))))))),
        ("Id <- [-a-z-]", Grammar(
            Rule(Identifier('Id'),
                 Expression(Alt(
                     Part(metaname=None,
                          prime=Class(
                              Range(Char('-')),
                              Range(Char('a'), Char('z')),
                              Range(Char('-'))))))))),
    ]
