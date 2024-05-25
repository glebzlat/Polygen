import unittest
import sys
import inspect

from io import StringIO
from datetime import datetime
from tempfile import TemporaryDirectory
from pathlib import Path

from polygen.parsing.bootstrap.parser import Parser as GrammarParser
from polygen.grammar.tree_modifier import (
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
    DetectLeftRec,
    TreeModifier,
    TreeModifierWarning
)

from polygen.generator.preprocessor import FilePreprocessor
from polygen.backend.python import Generator as PythonGenerator
from polygen.__version__ import __version__

DATEFORMAT = "%Y-%m-%d %I:%M %p"
SKEL_FILE = (Path.cwd() / 'polygen' / 'parsing' /
             'bootstrap' / 'parser.py.skel')
TMPDIR = TemporaryDirectory()
TMPDIR_PATH = Path(TMPDIR.name)


class SkipCase:
    """Used to skip test cases."""

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason

    def __repr__(self):
        return f'SkipCase({self.reason})'


class ParserTestMetaClass(type):
    """Metaclass for generated parsers tests.

    Classes that inherit from this class should define the following
    attributes:
        grammar: Grammar to generate the parser from. Required.
        modifiers: A list of modifiers to modify the grammar before the
            parser is generated.
        successes: A list of tuples tuple[Skip?, Input, Result], where
            the Input is a string to be parsed and Result is the expected
            result. If the Skip is present, then this case will be skipped.
        failures: A list of input strings, where each string expected to
            cause parsing failure.
    """

    @classmethod
    def create_parser(cls, idx, cls_name, grammar, modifiers):
        parser = GrammarParser(grammar)
        tree = parser.parse()

        assert tree is not None, "parsing failure"

        modifier = TreeModifier(modifiers)
        try:
            modifier.visit(tree)
        except TreeModifierWarning:
            pass

        stream = StringIO()
        gen = PythonGenerator(tree, stream)
        gen.generate()
        stream.seek(0)

        directives = {
            "body": stream.read(),
            "entry": tree.entry.id.string,
            "version": __version__,
            "datetime": datetime.today().strftime(DATEFORMAT)
        }

        proc = FilePreprocessor(directives)
        input_file = SKEL_FILE

        tmpdir = TMPDIR_PATH / f'test_generated_parser_{cls_name}'
        if tmpdir.exists():
            tmpdir.rmdir()
        tmpdir.mkdir()

        module_name = f'_test_parser_{idx}'
        output_file = tmpdir / f'{module_name}.py'

        proc.process({input_file: output_file})

        sys.path.append(str(tmpdir))
        module = __import__(module_name)
        sys.path.pop()
        return module.Parser

    def __init__(cls, name, bases, body):
        if name == 'ParserTest':
            return

        grammar = cls.grammar
        modifiers = cls.modifiers
        successes = getattr(cls, 'successes', [])
        failures = getattr(cls, 'failures', [])

        lineno = inspect.getsourcelines(cls)[1]
        cls_name = cls.__name__
        cls.parser = cls.create_parser(lineno, cls_name, grammar, modifiers)

        def add_success_case(idx, case):
            if len(case) == 3:
                skip, input_str, clue = case
            else:
                skip, input_str, clue = None, *case

            def wrapper(self):
                if skip is not None:
                    self.skipTest(skip.reason)
                parser = self.parser(input_str)
                # breakpoint()
                result = parser.parse()
                try:
                    self.assertIsNotNone(result)
                    self.assertEqual(result, clue)
                except AssertionError as e:
                    type_name = cls.__name__
                    msg = f"{type_name}:{lineno}: {e}"
                    raise AssertionError(msg) from None

            setattr(cls, f'test_parses_{idx}', wrapper)

        for i, case in enumerate(successes, 1):
            add_success_case(i, case)

        def add_failure_case(idx, case):
            input_str = case

            def wrapper(self):
                parser = self.parser(input_str)
                result = parser.parse()
                try:
                    self.assertIsNone(result)
                except AssertionError as e:
                    type_name = cls.__name__
                    msg = f"{type_name}:{lineno}: {e}"
                    raise AssertionError(msg) from None

            setattr(cls, f'test_fails_{idx}', wrapper)

        for i, case in enumerate(failures, 1):
            add_failure_case(i, case)


bases = (unittest.TestCase,)
ParserTest = ParserTestMetaClass('ParserTest', bases, {})


class TestSimpleGrammar(ParserTest):
    grammar = """
    @entry
    Grammar <- "abc" EOF
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('abc', ('abc', True))
    ]

    failures = [
        '',
        'ab',
        ' abc',
        'abc '
    ]


class TestNoEof(ParserTest):
    grammar = """
    @entry
    Grammar <- "abc"
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('abc', 'abc'),
        ('abcde', 'abc')
    ]


class TestEmptyAlt(ParserTest):
    grammar = """
    @entry
    Empty <-
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('', True)
    ]


class TestRightRecursiveGrammar(ParserTest):
    grammar = """
    @entry
    A <- 'a' B
    B <- 'b' C
    C <- 'c' D / 'c' A
    D <- 'd'
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('abcd', ('a', ('b', ('c', 'd')))),
        ('abcabcd', ('a', ('b', ('c', ('a', ('b', ('c', 'd')))))))
    ]

    failures = [
        '',
        'a',
        'd',
        'abca'
    ]


class TestZeroOrOne(ParserTest):
    grammar = """
    @entry
    A <- 'a' B? EOF
    B <- 'b'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('ab', ('a', 'b', True)),
        ('a', ('a', True, True))
    ]

    failues = [
        'abb'
    ]


class TestZeroOrMore(ParserTest):
    grammar = """
    @entry
    A <- 'a' B* EOF
    B <- 'b'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a', ('a', [], True)),
        ('abb', ('a', ['b', 'b'], True)),
        ('abbb', ('a', ['b', 'b', 'b'], True)),
    ]


class TestOneOrMore(ParserTest):
    grammar = """
    @entry
    A <- 'a' B+ EOF
    B <- 'b'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('ab', ('a', ['b'], True)),
        ('abbb', ('a', ['b', 'b', 'b'], True)),
    ]

    failures = [
        'a'
    ]


class TestRepetition(ParserTest):
    grammar = """
    @entry
    Grammar <- A{2,4} EOF
    A <- 'a'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        (SkipCase('work in progress'), 'aa', (('a', 'a'), True)),
        (SkipCase('work in progress'), 'aaa', (('a', 'a', 'a'), True)),
        ('aaaa', (('a', 'a', 'a', 'a'), True))
    ]

    failures = [
        'a',
        'aaaaa'
    ]


class TestRepetitionNoExpand(ParserTest):
    grammar = """
    @entry
    Grammar <- A{2,4} EOF
    A <- 'a'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep(apply=False)],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('aa', (('a', 'a'), True)),
        ('aaa', (('a', 'a', 'a'), True)),
        ('aaaa', (('a', 'a', 'a', 'a'), True))
    ]

    failures = [
        'a',
        'aaaaa'
    ]


class TestExpression(ParserTest):
    grammar = """
    @entry
    Grammar <- (A / B / C)+ '.' EOF
    A <- 'a'
    B <- 'b'
    C <- 'c'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a.', (['a'], '.', True)),
        ('b.', (['b'], '.', True)),
        ('c.', (['c'], '.', True)),
        ('abc.', (['a', 'b', 'c'], '.', True)),
        ('cba.', (['c', 'b', 'a'], '.', True))
    ]


class TestNestedQuantifiers(ParserTest):
    grammar = """
    @entry
    Grammar <- (A / B)+ '.' EOF
    A <- 'a'*
    B <- 'b'+
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a.', ([['a']], '.', True)),
        (SkipCase("work in progress"), 'b.', ()),
        (SkipCase("work in progress"), 'ab.', ()),
        (SkipCase("work in progress"), 'aaabbbaaa.', ())
    ]


class TestNestedRepetitions(ParserTest):
    grammar = """
    @entry
    Grammar <- (A / B){2,3} '.' EOF
    A <- 'a'{3,5} Space
    B <- 'b'{1,3} Space
    Space <- ' '?
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('aaaaa aaaa.', (((('a', 'a', 'a', 'a', 'a'), ' '),
                          (('a', 'a', 'a', 'a', True), True), True),
                         '.', True)),
        ('bbb b.', (((('b', 'b', 'b'), ' '),
                     (('b', True, True), True), True), '.', True)),
        ('aaa b aaaa.', (((('a', 'a', 'a', True, True), ' '),
                          (('b', True, True), ' '),
                          (('a', 'a', 'a', 'a', True), True)),
                         '.',
                         True))
    ]

    failures = [
        'b b b b'
    ]


class TestClass(ParserTest):
    grammar = """
    @entry
    Symbol <- [a-zA-Z0-9]
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a', 'a'),
        ('z', 'z'),
        ('A', 'A'),
        ('0', '0'),
        ('9', '9')
    ]

    failures = ['_', '-', ',']


class TestClassNoExpand(ParserTest):
    grammar = """
    @entry
    Symbol <- [a-zA-Z0-9]
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(apply=False), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a', 'a'),
        ('z', 'z'),
        ('A', 'A'),
        ('0', '0'),
        ('9', '9')
    ]

    failures = ['_', '-', ',']

class TestChars(ParserTest):
    grammar = r"""
    @entry
    Char <- A / One / Pi
    A <- '\141'
    One <- '\61'
    Pi <- '\u03c0'
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('\61', '\61'),
        ('\141', '\141'),
        (SkipCase("work in progress"), '\u03c0', '\u03c0')
    ]


class TestMetaRule(ParserTest):

    # this test may be incorrect, because here floating points are compared
    # using equality

    grammar = """
    @entry
    Float <- i:Digit+ '.' f:Digit+ $float_action
    Digit <- [0-9]

    $float_action {
        integer_part = ''.join(i)
        floating_part = ''.join(f)
        return float(f'{integer_part}.{floating_part}')
    }
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('3.1415', 3.1415)
    ]

    failures = [
        '3',
        '.14'
    ]


class TestIgnorePart(ParserTest):
    grammar = """
    @entry
    Grammar <- Char _:'-' Char EOF
    Char <- [a-z]
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a-b', ('a', 'b', True))
    ]


class TestIgnoreRule(ParserTest):
    grammar = """
    @entry
    Grammar <- Char+ EOF
    Char <- [a-z] Space

    @ignore
    Space <- ' '*

    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        ('a   b  cd ', (['a', 'b', 'c', 'd'], True))
    ]


class TestIgnoreRuleUnignored(ParserTest):
    grammar = """
    @entry
    Grammar <- Char+ EOF
    Char <- [a-z] s:Space

    @ignore
    Space <- ' '

    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
    ]

    successes = [
        (SkipCase("work in progress"),
         'a b c d ', (['a', ' ', 'b', ' ', 'c', ' ', 'd', ' '], True))
    ]


class TestDirectLeftRecursion(ParserTest):
    grammar = """
    @entry
    Grammar <- Expr EOF
    Expr <- Expr '+' Term / Expr '-' Term / Term
    Term <- Term '*' Number / Term '/' Number / Number
    Number <- [0-9]

    # XXX: There is a bug in tree modifier rules, that I can't catch for now:
    # if EOF rule is not defined, then no exception is raised
    # (though UndefRuleError expected). Instead, program falls in
    # DetectLeftRec with KeyError.

    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
        [DetectLeftRec()]
    ]

    successes = [
        ('1', ('1', True)),
        ('1+2', (('1', '+', '2'), True)),
        ('1+2+3+4+5+6+7+8+9', ((((((((('1', '+', '2'),
                                      '+', '3'),
                                     '+', '4'),
                                    '+', '5'),
                                   '+', '6'),
                                  '+', '7'),
                                 '+', '8'),
                                '+', '9'), True)),
        ('1-2-3-4-5-6-7-8-9', ((((((((('1', '-', '2'),
                                      '-', '3'),
                                     '-', '4'),
                                    '-', '5'),
                                   '-', '6'),
                                  '-', '7'),
                                 '-', '8'),
                                '-', '9'), True)),
        ('1-2+3-4+5-6+7-8+9', ((((((((('1', '-', '2'),
                                      '+', '3'),
                                     '-', '4'),
                                    '+', '5'),
                                   '-', '6'),
                                  '+', '7'),
                                 '-', '8'),
                                '+', '9'), True)),
        ('1+2-3+4-5+6-7+8-9', ((((((((('1', '+', '2'),
                                      '-', '3'),
                                     '+', '4'),
                                    '-', '5'),
                                   '+', '6'),
                                  '-', '7'),
                                 '+', '8'),
                                '-', '9'), True)),

        ('1+2*3', (('1', '+', ('2', '*', '3')), True)),
        ('6-3*2', (('6', '-', ('3', '*', '2')), True)),
        ('1*2+3', ((('1', '*', '2'), '+', '3'), True)),

        ('4+3/3', (('4', '+', ('3', '/', '3')), True)),
        ('2-6/3', (('2', '-', ('6', '/', '3')), True)),
        ('8/4-2', ((('8', '/', '4'), '-', '2'), True)),

        ('2*2/2', ((('2', '*', '2'), '/', '2'), True)),
        ('6/2*3', ((('6', '/', '2'), '*', '3'), True)),

        ('8/4/2', ((('8', '/', '4'), '/', '2'), True)),
        ('2*2*2', ((('2', '*', '2'), '*', '2'), True))
    ]


class TestHiddenLeftRecursion_Simple(ParserTest):
    grammar = """
    @entry
    Grammar <- Expr EOF
    Expr <- Opt? Expr '+' Term / Term
    Opt <- '-'
    Term <- [0-9]
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
        [DetectLeftRec()]
    ]

    successes = [
        ('1', ('1', True)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1', (('-', '1'), True)),
        ('1+2', ((True, '1', '+', '2'), True)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1+2', (('-', '1', '+', '2'), True)),
    ]


class TestHiddenLeftRecursion_Complicated(ParserTest):
    grammar = """
    @entry
    Grammar <- Expr EOF
    Expr <- A Expr '+' Term / Term
    A <- Id '=' / '-'?
    Id <- [a-z]
    Term <- [0-9]
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
        [DetectLeftRec()]
    ]

    successes = [
        ('1', ('1', True)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1', (('-', '1'), True)),
        ('1+2', ((True, '1', '+', '2'), True)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1+2', (('-', '1', '+', '2'), True)),
        (SkipCase('there is a bug in DetectLeftRec'),
         'a=1+1', ((('a', '='), '1', '+', '1'), True)),
    ]


class TestIndirectLeftRecursion_OneBranch(ParserTest):
    grammar = """
    @entry
    Grammar <- A EOF
    A <- B 'a'
    B <- C 'b'
    C <- A 'c' / D 'c'
    D <- 'd'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
        [DetectLeftRec()]
    ]

    successes = [
        ('dcba', (((('d', 'c'), 'b'), 'a'), True)),
        ('dcbacbacba', (((((((((('d',
                                 'c'),
                                'b'),
                               'a'),
                              'c'),
                             'b'),
                            'a'),
                           'c'),
                          'b'),
                         'a'), True))
    ]


class TestIndirectLeftRecursion_TwoBranches(ParserTest):
    grammar = """
    @entry
    Grammar <- A EOF
    A <- B 'a' / E 'a'
    B <- C 'b'
    C <- A 'c' / D 'c'
    D <- 'd'
    E <- F 'e'
    F <- A 'f' / G 'f'
    G <- 'g'
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
        [DetectLeftRec()]
    ]

    successes = [
        ('dcba', (((('d', 'c'), 'b'), 'a'), True)),
        ('gfea', (((('g', 'f'), 'e'), 'a'), True)),
        ('gfeafeafea', (((((((((('g',
                                 'f'),
                                'e'),
                               'a'),
                              'f'),
                             'e'),
                            'a'),
                           'f'),
                          'e'),
                         'a'), True)),
        (SkipCase('annoying bug'),
         'dcbafea', ((((((('d', 'c'), 'b'), 'a'), 'f'), 'e'), 'a'), True)),
        ('gfeacba', ((((((('g', 'f'), 'e'), 'a'), 'c'), 'b'), 'a'), True))
    ]


class TestInterlockingLeftRecursion(ParserTest):
    grammar = """
    # This grammar is adopted from here:
    # https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion

    @entry
    Grammar <- L EOF
    L <- P '.x' / 'x'
    P <- P '(n)' / L
    EOF <- !.
    """

    modifiers = [
        [SubstituteMetaRefs()],
        [CreateAnyCharRule()],
        [ExpandClass(), ReplaceRep()],
        [FindEntryRule(), IgnoreRules()],
        [SimplifyNestedExps(), ReplaceNestedExps()],
        [CheckUndefRedef()],
        [GenerateMetanames()],
        [DetectLeftRec()]
    ]

    successes = [
        ('x', ('x', True)),
        ('x.x', (('x', '.x'), True)),
        (SkipCase('work in progress'),
         'x(n)(n).x', (((('x', '(n)'), '(n)'), '.x'), True))
    ]
