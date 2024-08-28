import logging

from io import StringIO
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from polygen.__version__ import __version__
from polygen.node import Grammar, GrammarVisitor
from .preprocessor import (
    check_undefined_directives_batch,
    process_batch,
    create_output_filename
)
from .config import Option


class CodeGeneratorError(Exception):
    pass


class CodeGeneratorBase(GrammarVisitor):

    # These variables are set by backend's code generator
    NAME: str
    LANGUAGE: str
    VERSION: str
    FILES: list[str]
    RESERVED_WORDS: set[str]
    OPTIONS: Optional[dict[str, Option]]

    # Directory where the backend files are placed - set by polygen
    backend_dir: Path

    logger = logging.getLogger("polygen.codegen")

    def _create_directives(self):
        with self.directive("polygen_version"):
            self.put(__version__)
        with self.directive("generator"):
            self.put(self.NAME)
        with self.directive("gen_version"):
            self.put(self.VERSION)
        with self.directive("header"):
            pass

    def __init__(self, line_ending="", newline="\n", verbose=False):
        self._indentation = ''
        self._indent_level = 0
        self._directives: dict[str, StringIO] = {}
        self._directive: str | None = None

        self.line_ending = line_ending
        self.newline = newline
        self.verbose = verbose

        self._create_directives()

    @contextmanager
    def directive(self, name: str, indent_level: int = 0):
        """Redirect data to directive.

        `put` methods, called in the body of the `directive` context manager,
        print the data into a stream, associated with this directive. The
        data from the stream will be read by the preprocessor in order to
        replace directive entry.

        Args:
            name: Directive name
        """
        save = self._directive
        indent_save = self._indentation
        level_save = self._indent_level
        try:
            self._directive = name
            self._directives.setdefault(self._directive, StringIO())
            self._indentation = '    ' * indent_level
            self._indent_level = indent_level
            yield
        finally:
            self._directive = save
            self._indentation = indent_save
            self._indent_level = level_save

    def put(self,
            *args: Any,
            newline=True,
            indent=True,
            line_ending=True) -> None:
        """Print arguments to stream.

        Args:
            args: Arguments
            newline: Put newline at the end
            indent: Indent a line
            line_ending: Put a line ending at the end of a line
        """
        if self._directive is None:
            raise ValueError("provide a directive to put content into")
        file = self._directives[self._directive]
        if indent:
            print(end=self._indentation, file=file)
        end = self.line_ending if line_ending else ""
        print(*args, end=end, file=file)
        if newline:
            print(self.newline, end="", file=file)

    @contextmanager
    def indent(self, level: int = 1):
        """Increase indentation level.

        Args:
            level: Level by which the current indentation level is increased
        """
        save = self._indentation
        try:
            self._indentation += '    ' * level
            self._indent_level += level
            yield
        finally:
            self._indentation = save
            self._indent_level -= level

    def emptyline(self) -> None:
        """Put empty line.

        Empty line contains newline character only.
        """
        self.put(indent=False, line_ending=False)

    @abstractmethod
    def generate(self, grammar: Grammar, options: dict[str, Any]):
        raise NotImplementedError

    def create_files(self, directory: Path) -> dict[str, Path]:
        input_files = {
            self.backend_dir / f:
            directory / create_output_filename(f, add_stem=False)
            for f in self.FILES
        }

        for d in self._directives.values():
            if isinstance(d, StringIO):
                d.seek(0)

        undef = check_undefined_directives_batch(
            self._directives, input_files.keys())
        if undef:
            lines = '\n'.join(f"  {d}" for d in undef)
            message = f"undefined directives:\n{lines}"
            raise CodeGeneratorError(message)
        process_batch(self._directives, input_files)

        return {fin.name: fout for fin, fout in input_files.items()}

    def cleanup(self):
        self._directives.clear()
        self._create_directives()
