import os
import unittest

from dataclasses import dataclass
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Optional

from polygen.preprocessor import (
    process,
    ParserFailed,
    IncludeNotFound,
    CircularIncludeError
)
from polygen.node import (
    Grammar,
    Rule,
    MetaRef,
    MetaRule,
    Expr,
    Alt,
    NamedItem,
    Id,
    String,
    Char
)


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
        try:
            tree = process(self.entry, [self.base_dir])
        except Exception as e:
            if self.exception:
                self.assertIsInstance(e, self.exception)
                return

            self.fail(f"exception raised by the process: {e}")

        inspect = getattr(self, "inspect", None)
        if inspect:
            inspect(tree)

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
        Rule(Id('Rule'), Expr([
            Alt([NamedItem(None, Char('a'))])
        ])),
        Rule(Id('Grammar'), Expr([
            Alt([NamedItem(None, Id('Rule'))])
        ]), entry=True)
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
        Rule(Id('Rule'), Expr([
            Alt([NamedItem(None, Char('a'))])
        ])),
        Rule(Id('Grammar'), Expr([
            Alt([NamedItem(None, Id('Rule'))])
        ]), entry=True)
    ])


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
        Rule(Id('Rule'), Expr([
            Alt([NamedItem(None, Char('a'))])
        ])),
        Rule(Id('Grammar'), Expr([
            Alt([NamedItem(None, Id('Rule'))])
        ]), entry=True)
    ])


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

    exception = ParserFailed


class TestIncludeNotFound(TestBase, unittest.TestCase):
    input_files = [
        File("grammar.peg", """
@include "include1.peg"

@entry
Grammar <- Rule
""", entry=True)
    ]

    exception = IncludeNotFound
