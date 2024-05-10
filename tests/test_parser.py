import unittest

from polygen.parsing import Parser
from polygen.grammar.node import (
    Node,
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
                print(repr(result))
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
