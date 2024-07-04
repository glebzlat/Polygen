import unittest
import inspect

from tempfile import TemporaryDirectory
from pathlib import Path

from polygen.codegen import CodeGenerator, CodeGeneratorError

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
    def create_parser(cls, idx, cls_name, grammar, capabilities: dict):
        gen = CodeGenerator.setup()

        tmpdir = TMPDIR_PATH / f'test_generated_parser_{cls_name}'
        if tmpdir.exists():
            tmpdir.rmdir()
        tmpdir.mkdir()

        capabilities = {f'capabilities.{name}': value
                        for name, value in capabilities.items()}

        module_file = tmpdir / 'parser.py'
        try:
            gen.generate('python', tmpdir, modifier_options=capabilities,
                         grammar=grammar)
        except CodeGeneratorError as e:
            raise RuntimeError(f"{cls_name}:{idx}: {e}") from None

        namespace = {}
        with open(module_file, 'rb') as fin:
            code = compile(fin.read(), fin.name, 'exec')
        exec(code, namespace)

        return namespace['Parser']

    def __init__(cls, name, bases, body):
        if name == 'ParserTest':
            return

        grammar = cls.grammar
        capabilities = {}
        successes = getattr(cls, 'successes', [])
        failures = getattr(cls, 'failures', [])

        lineno = inspect.getsourcelines(cls)[1]
        cls_name = cls.__name__
        cls.parser = cls.create_parser(lineno, cls_name, grammar, capabilities)

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
                    self.assertEqual(result.value, clue)
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

    successes = [
        ('abc', ('abc',))
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

    successes = [
        ('abc', 'abc'),
        ('abcde', 'abc')
    ]


class TestEmptyAlt(ParserTest):
    grammar = """
    @entry
    Empty <-
    """

    successes = [
        ('', None)
    ]


class TestRightRecursiveGrammar(ParserTest):
    grammar = """
    @entry
    A <- 'a' B
    B <- 'b' C
    C <- 'c' D / 'c' A
    D <- 'd'
    """

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

    successes = [
        ('ab', ('a', 'b')),
        ('a', ('a',))
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

    successes = [
        ('a', ('a', [])),
        ('abb', ('a', ['b', 'b'])),
        ('abbb', ('a', ['b', 'b', 'b'])),
    ]


class TestOneOrMore(ParserTest):
    grammar = """
    @entry
    A <- 'a' B+ EOF
    B <- 'b'
    EOF <- !.
    """

    successes = [
        ('ab', ('a', ['b'])),
        ('abbb', ('a', ['b', 'b', 'b'])),
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

    successes = [
        ('aa', (('a', 'a'),)),
        ('aaa', (('a', 'a', 'a'),)),
        ('aaaa', (('a', 'a', 'a', 'a'),))
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

    successes = [
        ('a.', (['a'], '.')),
        ('b.', (['b'], '.')),
        ('c.', (['c'], '.')),
        ('abc.', (['a', 'b', 'c'], '.')),
        ('cba.', (['c', 'b', 'a'], '.'))
    ]


class TestNestedQuantifiers(ParserTest):
    grammar = """
    # If A is placed before B, then B will never succeed, because a*
    # succeeds even if no input was consumed.
    @entry
    Grammar <- (B / A)+ '.' EOF
    A <- 'a'*
    B <- 'b'+
    EOF <- !.
    """

    successes = [
        ('a.', ([['a']], '.')),
        ('b.', ([['b']], '.')),
        ('ab.', ([['a'], ['b']], '.')),
        ('aaabbbaaa.', ([['a', 'a', 'a'],
                         ['b', 'b', 'b'],
                         ['a', 'a', 'a']], '.'))
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

    successes = [
        ('aaaaa aaaa.', (((('a', 'a', 'a', 'a', 'a'), ' '),
                          ((('a', 'a', 'a', 'a'),))), '.')),
        ('bbb b.', (((('b', 'b', 'b'), ' '),
                     (('b',),)), '.')),
        ('aaa b aaaa.', (((('a', 'a', 'a'), ' '),
                          (('b',), ' '),
                          ((('a', 'a', 'a', 'a'),))),
                         '.'))
    ]

    failures = [
        'b b b b'
    ]


class TestClass(ParserTest):
    grammar = """
    @entry
    Symbol <- [a-zA-Z0-9]
    """

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

    successes = [
        ('\61', '\61'),
        ('\141', '\141'),
        ('\u03c0', '\u03c0')
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
        return float(f'{integer_part\\}.{floating_part\\}')
    }
    """

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

    successes = [
        ('a-b', ('a', 'b'))
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

    successes = [
        ('a   b  cd ', (['a', 'b', 'c', 'd'],))
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

    successes = [
        ('a b c d ', ([('a', ' '), ('b', ' '), ('c', ' '), ('d', ' ')],))
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

    successes = [
        ('1', ('1',)),
        ('1+2', (('1', '+', '2'),)),
        ('1+2+3+4+5+6+7+8+9', ((((((((('1', '+', '2'),
                                      '+', '3'),
                                     '+', '4'),
                                    '+', '5'),
                                   '+', '6'),
                                  '+', '7'),
                                 '+', '8'),
                                '+', '9'),)),
        ('1-2-3-4-5-6-7-8-9', ((((((((('1', '-', '2'),
                                      '-', '3'),
                                     '-', '4'),
                                    '-', '5'),
                                   '-', '6'),
                                  '-', '7'),
                                 '-', '8'),
                                '-', '9'),)),
        ('1-2+3-4+5-6+7-8+9', ((((((((('1', '-', '2'),
                                      '+', '3'),
                                     '-', '4'),
                                    '+', '5'),
                                   '-', '6'),
                                  '+', '7'),
                                 '-', '8'),
                                '+', '9'),)),
        ('1+2-3+4-5+6-7+8-9', ((((((((('1', '+', '2'),
                                      '-', '3'),
                                     '+', '4'),
                                    '-', '5'),
                                   '+', '6'),
                                  '-', '7'),
                                 '+', '8'),
                                '-', '9'),)),

        ('1+2*3', (('1', '+', ('2', '*', '3')),)),
        ('6-3*2', (('6', '-', ('3', '*', '2')),)),
        ('1*2+3', ((('1', '*', '2'), '+', '3'),)),

        ('4+3/3', (('4', '+', ('3', '/', '3')),)),
        ('2-6/3', (('2', '-', ('6', '/', '3')),)),
        ('8/4-2', ((('8', '/', '4'), '-', '2'),)),

        ('2*2/2', ((('2', '*', '2'), '/', '2'),)),
        ('6/2*3', ((('6', '/', '2'), '*', '3'),)),

        ('8/4/2', ((('8', '/', '4'), '/', '2'),)),
        ('2*2*2', ((('2', '*', '2'), '*', '2'),))
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

    successes = [
        ('1', ('1',)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1', ('-', '1')),
        ('1+2', (('1', '+', '2'),)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1+2', ('-', '1', '+', '2')),
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

    successes = [
        (SkipCase('work in progress'), '1', ('1',)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1', ('-', '1')),
        (SkipCase('work in progress'), '1+2', (('1', '+', '2'),)),
        (SkipCase('there is a bug in DetectLeftRec'),
         '-1+2', ('-', '1', '+', '2')),
        (SkipCase('there is a bug in DetectLeftRec'),
         'a=1+1', (('a', '='), '1', '+', '1')),
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

    successes = [
        ('dcba', (((('d', 'c'), 'b'), 'a'),)),
        ('dcbacbacba', (((((((((('d',
                                'c'),
                               'b'),
                              'a'),
                             'c'),
                            'b'),
                           'a'),
                          'c'),
                         'b'),
                        'a'),))
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

    capabilities = {
        "leftrec": True,
        "repetition": False,
        "char-class": False
    }

    successes = [
        ('dcba', (((('d', 'c'), 'b'), 'a'),)),
        ('gfea', (((('g', 'f'), 'e'), 'a'),)),
        ('gfeafeafea', (((((((((('g',
                                'f'),
                               'e'),
                              'a'),
                             'f'),
                            'e'),
                           'a'),
                          'f'),
                         'e'),
                        'a'),)),
        ('dcbafea', ((((((('d', 'c'), 'b'), 'a'), 'f'), 'e'), 'a'),)),
        ('gfeacba', ((((((('g', 'f'), 'e'), 'a'), 'c'), 'b'), 'a'),))
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

    capabilities = {
        "leftrec": True,
        "repetition": False,
        "char-class": False
    }

    successes = [
        ('x', ('x',)),
        (SkipCase('work in progress'), 'x.x', (('x', '.x'),)),
        (SkipCase('work in progress'),
         'x(n)(n).x', ((('x', '(n)'), '(n)'), '.x'))
    ]
