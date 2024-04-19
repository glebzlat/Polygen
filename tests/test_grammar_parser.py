import unittest

from typing import Callable, Any
from itertools import repeat

from polygen.reader import Reader
from polygen.grammar_parser import GrammarParser
from polygen.node import (
    Rule,
    Range,
    Expression,
    Sequence,
    Identifier,
    Literal,
    Class,
    Predicate,
    Quantifier,
    Repetition,
    Char
)


P = GrammarParser


class Omit:
    pass


class TestGrammarParser(unittest.TestCase):

    def parse_success(self,
                      *cases: tuple[str, list[Callable]] |
                      tuple[str, list[Callable], list[Any | type[Omit]]]):
        for case in cases:
            string, events, *clue = case

            reader = Reader(string)
            parser = GrammarParser(reader)

            if (clue
                    and (clue := clue[0])
                    and (diff := len(events) - len(clue))):
                clue = list(clue) + list(repeat(Omit, times=diff))
            else:
                clue = repeat(Omit, times=len(events))

            for e, c in zip(events, clue):
                try:
                    result = e(parser)
                    self.assertTrue(result)
                    if c is not Omit:
                        self.assertEqual(result, c)
                except Exception as exc:
                    exc_name, fn_name = exc.__class__.__name__, e.__name__
                    msg = (f"SUCCESS CASE: {exc_name}: {exc} : "
                           f"function {fn_name} "
                           f"on input {string!r}")
                    raise Exception(msg) from None

    def parse_failure(self, *cases: str):
        for string, events in cases:
            reader = Reader(string)
            parser = GrammarParser(reader)
            event = events[0]
            try:
                self.assertIsNone(event(parser))
            except AssertionError as exc:
                exc_name, fn_name = exc.__class__.__name__, event.__name__
                msg = (f"FAILURE CASE: {exc_name}: {exc} : "
                       f"function {fn_name} "
                       f"on input {string!r}")
                raise Exception(msg) from None

    def test_EndOfFile(self):
        self.parse_success(("", [P._EndOfFile], [True]))

    def test_EndOfLine(self):
        self.parse_success(("\n", [P._EndOfLine, P._EndOfFile]))
        self.parse_success(("\r\n", [P._EndOfLine, P._EndOfFile]))
        self.parse_success(("\r", [P._EndOfLine, P._EndOfFile]))

    def test_Space(self):
        self.parse_success((" ", [P._Space, P._EndOfFile]))
        self.parse_success(("\n", [P._Space, P._EndOfFile]))

    def test_Comment(self):
        self.parse_success(("# abc\n", [P._Comment, P._EndOfFile]))
        self.parse_success(("#\n", [P._Comment, P._EndOfFile]))

    def test_LEFTARROW(self):
        self.parse_success(("<-", [P._LEFTARROW]))

    def test_SLASH(self):
        self.parse_success(("/", [P._SLASH]))

    def test_HexDigit(self):
        fn = [P._HexDigit, P._EndOfFile]
        self.parse_success(
            ("0", fn),
            ("1", fn),
            ("2", fn),
            ("9", fn),
            ("a", fn),
            ("d", fn),
            ("A", fn),
            ("F", fn)
        )
        self.parse_failure(
            ("G", fn)
        )

    def test_Number(self):
        fn = [P._Number, P._EndOfFile]
        self.parse_success(
            ("1", fn),
            ("12", fn),
            ("123", fn)
        )
        self.parse_failure(
            ("a", fn)
        )

    def test_Repetition(self):
        fn = [P._Repetition, P._EndOfFile]
        self.parse_success(
            ("{1}", fn, [Repetition(1)]),
            ("{123}", fn, [Repetition(123)]),
            ("{1,2}", fn, [Repetition(1, 2)]),
            ("{12,34}", fn, [Repetition(12, 34)]),
            ("{4}\n", fn)
        )
        self.parse_failure(
            ("{}", fn),
            ("{a}", fn),
            ("{1,}", fn),
            ("{,1}", fn),
            ("{1,a}", fn),
            ("{1, 2}", fn),
            ("1,2}", fn),
            ("{1", fn)
        )

    def test_Char(self):
        fn = [P._Char, P._EndOfFile]
        self.parse_success(
            (r"\141", fn, [Char('a')]),
            (r"\147", fn, [Char('g')]),
            (r"\47", fn, [Char("'")]),
            ("a", fn, [Char('a')]),
            (r"\n", fn, [Char('\n')]),
            (r"\r", fn, [Char('\r')]),
            (r"\t", fn, [Char('\t')]),
            (r"\\", fn, [Char('\\')]),
            (r"\u03c0", fn, [Char(0x03c0)]),
            (r"\u03C0", fn, [Char(0x03c0)]),
            (r"\u03C4", fn, [Char(0x03c4)])
        )
        self.parse_failure(
            (r"\148", fn),
            (r"\a41", fn),
            (r"\1", fn),
            ("", fn),
            (r"\u123", fn),
            (r"\a1234", fn),
            (r"\u12g4", fn),
            (r"\b", fn)
        )

    def test_Range(self):
        fn = [P._Range, P._EndOfFile]
        self.parse_success(
            ("a-z", fn, [Range(Char('a'), Char('z')), True]),
            ("0-9", fn, [Range(Char('0'), Char('9'))]),
            ("a", fn, [Range(Char('a'))]),
            ("--z", fn, [Range(Char('-'), Char('z'))]),
            ("---", fn, [Range(Char('-'), Char('-'))])
        )
        self.parse_failure(
            ("", fn)
        )

    def test_Class(self):
        fn = [P._Class, P._EndOfFile]
        self.parse_success(
            ("[]", fn, [Class()]),
            ("[]\n", fn, [Class()]),
            ("[a]", fn, [Class(Range(Char('a')))]),
            ("[a-z]", fn, [Class(Range(Char('a'), Char('z')))]),
            ("[0-9]", fn, [Class(Range(Char('0'), Char('9')))]),
            ("[abc]", fn, [
                Class(Range(Char('a')),
                      Range(Char('b')),
                      Range(Char('c')))
            ]),
            ("[a-z0-9]", fn, [
                Class(Range(Char('a'), Char('z')),
                      Range(Char('0'), Char('9')))
            ]),
            ("[a-zA-Z0-9_]", fn, [
                Class(Range(Char('a'), Char('z')),
                      Range(Char('A'), Char('Z')),
                      Range(Char('0'), Char('9')),
                      Range(Char('_')))
            ])
        )

    def test_Literal(self):
        fn = [P._Literal, P._EndOfFile]
        self.parse_success(
            (r"''", fn, [Literal(), True]),
            (r"'a'", fn, [Literal(Char('a'))]),
            (r"'\''", fn, [Literal(Char('\''))]),
            (r"'\\'", fn, [Literal(Char('\\'))]),
            (r'"\""', fn, [Literal(Char('\"'))]),
            (r'"\n"', fn, [Literal(Char('\n'))]),
            (r"'\141'", fn, [Literal(Char('a'))]),
            (r"'\u03c0'", fn, [Literal(Char(0x03c0))]),
            ("'a'\n", fn),
            ("'a'\r\n", fn),
            ('"a"\n', fn),
        )
        self.parse_failure(
            ("'\"", fn),
            ("\"'", fn),
            ("'\\'", fn),
            ('"\\"', fn),
            (r"'\u3c0'", fn)
        )

    def test_Identifier(self):
        fn = [P._Identifier, P._EndOfFile]
        self.parse_success(
            ("a", fn, [Identifier('a')]),
            ("abc", fn, [Identifier('abc')]),
            ("a1", fn, [Identifier('a1')]),
            ("a_123bc", fn, [Identifier('a_123bc')])
        )
        self.parse_failure(
            ("1", fn),
            ("(", fn),
            ("", fn)
        )

    def test_Primary(self):
        fn = [P._Primary, P._EndOfFile]
        self.parse_success(
            ("abc", fn, [Identifier('abc')]),
            ("'a'", fn, [Literal(Char('a'))]),
            ("[a]", fn, [Class(Range(Char('a')))]),
            (".", fn, ['.']),
            ("(Id)", fn, [
                Expression(Sequence((None, (Identifier('Id'), None))))
            ])
        )

    def test_Sequence(self):
        fn = [P._Sequence, P._EndOfFile]
        self.parse_success(
            ("Id", fn, [Sequence((None, (Identifier('Id'), None)))]),
            ("!Id", fn, [
                Sequence((Predicate(Predicate.NOT), (Identifier('Id'), None)))
            ]),
            ("&Id", fn, [
                Sequence((Predicate(Predicate.AND), (Identifier('Id'), None)))
            ]),
            ("Id?", fn, [
                Sequence(
                    (None,
                     (Identifier('Id'),
                      Quantifier(Quantifier.OPTIONAL)))
                )
            ]),
            ("Id*", fn, [
                Sequence(
                    (None,
                     (Identifier('Id'),
                      Quantifier(Quantifier.ZERO_OR_MORE)))
                )
            ]),
            ("Id+", fn, [
                Sequence(
                    (None,
                     (Identifier('Id'),
                      Quantifier(Quantifier.ONE_OR_MORE)))
                )
            ]),
            ("Id{1}", fn, [
                Sequence(
                    (None,
                     (Identifier('Id'),
                      Quantifier(Repetition(1))))
                )
            ]),
            ("!Id?", fn, [
                Sequence(
                    (Predicate(Predicate.NOT),
                     (Identifier('Id'),
                      Quantifier(Quantifier.OPTIONAL)))
                )
            ]),
            ("&Id?", fn, [
                Sequence(
                    (Predicate(Predicate.AND),
                     (Identifier('Id'),
                      Quantifier(Quantifier.OPTIONAL)))
                )
            ]),
            ("& Id *", fn, [
                Sequence(
                    (Predicate(Predicate.AND),
                     (Identifier('Id'),
                      Quantifier(Quantifier.ZERO_OR_MORE)))
                )
            ]),
            ("&\rId\n+", fn, [
                Sequence(
                    (Predicate(Predicate.AND),
                     (Identifier('Id'),
                      Quantifier(Quantifier.ONE_OR_MORE)))
                )
            ]),
        )

    def test_Expression(self):
        fn = [P._Expression, P._EndOfFile]
        self.parse_success(
            ("Alt", fn),
            ("Alt1 / Alt2", fn, [
                Expression(
                    Sequence((None, (Identifier("Alt1"), None))),
                    Sequence((None, (Identifier("Alt2"), None)))
                )
            ]),
            ("/ Alt", fn, [
                Expression(
                    Sequence(),
                    Sequence((None, (Identifier("Alt"), None)))
                )
            ]),
            ("/", fn, [Expression(Sequence(), Sequence())])
        )

    def test_Definition(self):
        fn = [P._Definition, P._EndOfFile]
        self.parse_success(
            ("Id <- Rule", fn, [
                Rule(
                    Identifier("Id"),
                    Expression(Sequence((None, (Identifier('Rule'), None))))
                )
            ])
        )
        self.parse_failure(
            ("Id Rule", fn),
            # ("Id <-", fn)  # should it be a failure case?
            ("<- Rule", fn)
        )

    def test_Grammar(self):
        fn = [P._Grammar]
        self.parse_success(
            ("Expr <- Expr '+' Term / Expr '-' Term / Term", fn),
            (
                """
                # This grammar was stolen from Guido Van Rossum:
                # https://medium.com/@gvanrossum_83706/building-a-peg-parser-d4869b5958fb
                Statement  <- Assignment / Expr
                Expr       <- Expr '+' Term / Expr '-' Term / Term
                Term       <- Term '*' Atom / Term '/' Atom / Atom
                Assignment <- Target '=' Expr
                Target     <- ID
                """, fn
            ),
        )
