import os
import unittest

from dataclasses import dataclass
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Optional

from polygen.preprocessor import (
    process,
    IncludeNotFound,
    CircularIncludeError,
    UnknownEntry
)
from polygen.node import (
    RuleNotFound,
    Grammar,
    Rule,
    Expr,
    Alt,
    NamedItem,
    Id,
    Char
)
from polygen.generator.base import CodeGeneratorBase


TEST_NAME = "test_grammar_preprocessor"
TEST_DIR = os.environ.get("POLYGEN_TEST_DIR")
if TEST_DIR:
    TEST_DIR = Path(TEST_DIR) / TEST_NAME
else:
    TMP_DIR = TemporaryDirectory()
    TEST_DIR = Path(TMP_DIR.name) / TEST_NAME


@dataclass
class File:
    name: str
    content: str
    dir: str = ""
    entry: bool = False


class MockCodeGen(CodeGeneratorBase):
    NAME = "mock"
    LANGUAGE = "Mock"
    VERSION = "0.0.0"
    FILES = []
    OPTIONS = {}

    def generate(self, grammar, options):
        pass


class PreprocessorTestBase:

    input_files: list[File]
    grammar: Optional[Grammar] = None
    exception: Optional[type] = None

    def setUp(self):
        base_dir = TEST_DIR / type(self).__name__
        base_dir.mkdir(exist_ok=True, parents=True)

        self.entry = None
        self.base_dir = base_dir
        for file in self.input_files:
            file_dir = base_dir / file.dir
            filename = file_dir / file.name

            if file.entry:
                assert not self.entry, "only one entry can be specified"
                self.entry = filename

            file_dir.mkdir(exist_ok=True, parents=True)
            filename.write_text(file.content)

        if not self.entry:
            self.fail("specify one entry")

    def test_process(self):
        gen = MockCodeGen()

        try:
            tree = process(
                self.entry,
                [self.base_dir],
                backend_name=MockCodeGen.NAME,
                generator=gen
            )
        except Exception as e:
            if self.exception:
                self.assertIsInstance(e, self.exception)
                return

            raise

        inspect = getattr(self, "inspect", None)
        if inspect:
            inspect(tree, gen)

        if self.grammar:
            self.assertEqual(tree, self.grammar)


TestBase = PreprocessorTestBase


class TestIncludeFile(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@include "include.peg"

@entry
Grammar <- Rule
""", entry=True),
        File("include.peg", """
Rule <- 'a'
""")
    ]

    grammar = Grammar([
        Rule(Id('Grammar'), Expr([
            Alt([NamedItem(None, Id('Rule'))])
        ]), entry=True),
        Rule(Id('Rule'), Expr([
            Alt([NamedItem(None, Char('a'))])
        ])),
    ])


class TestIncludeSubdirectory(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@include "subdir/include.peg"

@entry
Grammar <- Rule
""", entry=True),
        File("include.peg", """
Rule <- 'a'
""", dir="subdir")
    ]

    grammar = Grammar([
        Rule(Id('Grammar'), Expr([
            Alt([NamedItem(None, Id('Rule'))])
        ]), entry=True),
        Rule(Id('Rule'), Expr([
            Alt([NamedItem(None, Char('a'))])
        ])),
    ])

    def inspect(self, grammar: Grammar, gen):
        for r in grammar.rules.iter():
            if r.id.value == "Grammar":
                self.assertTrue(r.entry)
                return
        self.fail("Grammar rule not found")


class TestNestedInclude(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@include "include1.peg"

@entry
Grammar <- Rule
""", entry=True),
        File("include1.peg", """
@include "include2.peg"
"""),
        File("include2.peg", """
@include "include3.peg"
"""),
        File("include3.peg", """
Rule <- 'a'
""")
    ]

    grammar = Grammar([
        Rule(Id('Grammar'), Expr([
            Alt([NamedItem(None, Id('Rule'))])
        ]), entry=True),
        Rule(Id('Rule'), Expr([
            Alt([NamedItem(None, Char('a'))])
        ])),
    ])

    def inspect(self, grammar: Grammar, gen):
        for r in grammar.rules.iter():
            if r.id.value == "Grammar":
                self.assertTrue(r.entry)
                return
        self.fail("Grammar rule not found")


class TestCircularInclude(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@include "include1.peg"

@entry
Grammar <- Rule
""", entry=True),
        File("include1.peg", """
@include "include2.peg"
"""),
        File("include2.peg", """
@include "include1.peg"
""")
    ]

    exception = CircularIncludeError


class TestParserFailed(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@entry
Grammar <- <- Rule
""", entry=True)
    ]

    exception = SyntaxError


class TestIncludeNotFound(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@include "include1.peg"

@entry
Grammar <- Rule
""", entry=True)
    ]

    exception = IncludeNotFound


class TestEntryDirective(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
             @entry Grammar

             Grammar <- Rule
             """, entry=True)
    ]

    def inspect(self, grammar: Grammar, gen):
        for r in grammar.rules.iter():
            if r.id.value == "Grammar":
                self.assertTrue(r.entry)
                return
        self.fail("Grammar rule not found")


class TestEntryNotFound(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
             @entry Foo

             Grammar <- Rule
             """, entry=True)
    ]

    exception = UnknownEntry


class TestEntryInAnotherFile(TestBase, unittest.TestCase):
    """
    @include directive handled before @entry, so @entry affects the
    merged grammar.
    """

    input_files = [
        File(
            "file1.peg",
            """
            @include "file2.peg"
            @entry Grammar

            Rule <- Foo
            """,
            entry=True
        ),
        File(
            "file2.peg",
            """
            Grammar <- Rule
            """
        )
    ]

    def inspect(self, grammar: Grammar, gen):
        for r in grammar.rules.iter():
            if r.id.value == "Grammar":
                self.assertTrue(r.entry)
                return
        self.fail("Grammar rule not found")


class TestIgnoreDirective(TestBase, unittest.TestCase):
    input_files = [
        File(
            "grammar.peg",
            """
            @ignore {
              Foo
              Bar
            }

            Foo <-
            Bar <-
            Baz <-
            """,
            entry=True
        )
    ]

    def inspect(self, grammar: Grammar, gen):
        self.assertTrue(grammar.get_rule("Foo").ignore)
        self.assertTrue(grammar.get_rule("Bar").ignore)
        self.assertFalse(grammar.get_rule("Baz").ignore)


class TestToplevelDirective(TestBase, unittest.TestCase):
    input_files = [
        File(
            "file1.peg",
            """
            Foo <-
            Bar <-

            @toplevel {
            @entry Foo

            Baz <-
            }
            """,
            entry=True
        )
    ]

    def inspect(self, grammar: Grammar, gen):
        self.assertTrue(grammar.get_rule("Foo").entry)
        try:
            grammar.get_rule("Baz")
        except RuleNotFound:
            self.fail("Rule Baz must be in the grammar")


class TestToplevelNested(TestBase, unittest.TestCase):
    input_files = [
        File(
            "file1.peg",
            """
            Foo <-
            Bar <-

            @toplevel {
            @entry Foo

            Baz <-
            }
            """
        ),
        File(
            "file2.peg",
            """
            @include "file1.peg"

            @entry
            Rule <-
            """,
            entry=True
        )
    ]

    def inspect(self, grammar: Grammar, gen):
        self.assertRaises(RuleNotFound, grammar.get_rule, "Baz")
        self.assertTrue(grammar.get_rule("Rule").entry)
        self.assertFalse(grammar.get_rule("Foo").entry)


class TestBackendDef(TestBase, unittest.TestCase):
    input_files = [
        File(
            "file.peg",
            """
            @backend.header {hello world}
            """,
            entry=True
        )
    ]

    def inspect(self, grammar, gen: MockCodeGen):
        self.assertIn("header", gen._directives)
        self.assertEqual(gen._directives["header"].getvalue(), "hello world\n")


class TestBackendDefAppend(TestBase, unittest.TestCase):
    input_files = [
        File(
            "file.peg",
            """
            @backend.header {hello world}

            @backend.header {hello world}
            """,
            entry=True
        )
    ]

    def inspect(self, grammar, gen: MockCodeGen):
        self.assertIn("header", gen._directives)
        self.assertEqual(
            gen._directives["header"].getvalue(),
            "hello world\nhello world\n"
        )


class TestBackendDefIncludeAppend(TestBase, unittest.TestCase):
    """`file2` processed before `@backend` directive in `file1`."""

    input_files = [
        File(
            "file1.peg",
            """
            @include "file2.peg"
            @backend.header {a}
            """,
            entry=True
        ),
        File(
            "file2.peg",
            """
            @backend.header {b}
            """
        ),
    ]

    def inspect(self, grammar, gen: MockCodeGen):
        self.assertIn("header", gen._directives)
        self.assertEqual(gen._directives["header"].getvalue(), "b\na\n")


class TestBackendDefAppendInclude(TestBase, unittest.TestCase):
    """
    `file2` processed after `@backend` directive in `file1`.

    First `file1`'s `@backend.header` contents inserted, then `file2`'s.
    """

    input_files = [
        File(
            "file1.peg",
            """
            @backend.header {a}
            @include "file2.peg"
            """,
            entry=True
        ),
        File(
            "file2.peg",
            """
            @backend.header {b}
            """
        ),
    ]

    def inspect(self, grammar, gen: MockCodeGen):
        self.assertIn("header", gen._directives)
        self.assertEqual(gen._directives["header"].getvalue(), "a\nb\n")


class TestBackendQuery(TestBase, unittest.TestCase):
    input_files = [
        File(
            "grammar.peg",
            """
            Foo <-
            Bar <-

            @backend(mock) {
              @entry Foo

              Faz <-
            }

            @backend(python) {
              @entry Bar

              Baz <-
            }
            """,
            entry=True
        )
    ]

    def inspect(self, grammar: Grammar, gen):
        self.assertTrue(grammar.get_rule("Foo").entry)
        self.assertFalse(grammar.get_rule("Bar").entry)

        try:
            grammar.get_rule("Faz")
        except RuleNotFound:
            self.fail("Faz rule must be in the grammar")


class TestNestedQueries(TestBase, unittest.TestCase):
    input_files = [
        File(
            "grammar.peg",
            """
            # 1st step: included first
            Foo <-

            @backend(mock) {
              # 1st step: included second
              Bar <-

              # 1st step: merged to the grammar
              @backend(mock) {
                # 2nd step: included forth
                Baz <-

                # 2nd step: merged to the grammar
                @toplevel {
                  # 3rd step: included last
                  Far <-
                }
              }
            }

            @toplevel {
              # 1st step: included third
              Faz <-
            }
            """,
            entry=True
        )
    ]

    grammar = Grammar([
        Rule(Id("Foo"), Expr([Alt([])])),
        Rule(Id("Bar"), Expr([Alt([])])),
        Rule(Id("Faz"), Expr([Alt([])])),
        Rule(Id("Baz"), Expr([Alt([])])),
        Rule(Id("Far"), Expr([Alt([])])),
    ], [])
