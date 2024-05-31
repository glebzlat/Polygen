import re
import sys

from io import TextIOBase, TextIOWrapper, StringIO
from typing import TextIO, Iterable, Optional, overload
from pathlib import Path


class PreprocessorError(Exception):
    """Preprocessor exceptions base."""


class NoSuchDirective(PreprocessorError):
    """Directive in the skeleton file not found in a dictionary."""

    def __init__(self, directive: str, lineno: int, filename: str):
        self.directive = directive
        self.lineno = lineno
        self.filename = filename

    def __eq__(self, other):
        if isinstance(other, NoSuchDirective):
            return ((self.directive, self.lineno, self.filename) ==
                    (other.directive, other.lineno, other.filename))
        return NotImplemented


class FilePreprocessorError(Exception):
    """Container for PreprocessorError exceptions.

    When Preprocessor raises an exception for one file, FilePreprocessor
    continues processing other files to collect all errors at once.
    """

    def __init__(self, *errors: PreprocessorError):
        self.errors = errors

    def __repr__(self):
        type_name = type(self).__name__
        parts = ', '.join(repr(e) for e in self.errors)
        return f'{type_name}({parts})'

    def __str__(self):
        return repr(self)


class Preprocessor:
    r"""Processes data from input stream and writes to output stream.

    Preprocessor's work is to process directives in the input data. When
    it finds a directive, it searches it in its directives dictionary and,
    if such directive found, replaces it with its substitution, otherwise
    raises an error.

    Directives are words, enclosed in two percent symbols '%':

        %% directive %%

    Directive name may consist of any word characters (that are matched
    by `\w` regex).

    Preprocessor preserves the prefix, the part of the string from the
    last newline character to the first percent symbol, for each line
    of the substitution. Also it preserves the original postfix, the part
    of the string from the last percent symbol up to the first newline,
    but places it only at the end of the substitution.

    Lines that don't contain directives are written without changes.
    """

    _DIRECTIVE_RE = re.compile(r'(.*)(?<!\\)%% *(\w+) *%%(.*)\Z',
                               flags=re.DOTALL)
    _NEWLINE_RE = re.compile(r'\A\n\r?\Z')

    ENCODING = 'utf-8'

    def __init__(self, directives: dict[str, str]):
        """Initialize Preprocessor.

        Arguments:
            directives: A mapping from the directive name to its substitution.
        """
        self.directives = directives

    def _insert(self,
                content: str | TextIO,
                ostream: TextIO,
                prefix: str,
                postfix: str) -> None:
        istream = StringIO(content) if isinstance(content, str) else content

        for line in istream:
            if self._NEWLINE_RE.match(line):
                ostream.write(line)
            else:
                ostream.write(prefix + line)
        ostream.write(postfix)

    def check_stream(self, istream: TextIOBase):
        """Check input stream for errors.

        Iterates over lines in the stream and raises an exception
        if finds an error. Moves the stream pointer to the beginning of
        the stream anyway.

        Args:
            istream: Input stream.

        Raises:
            ValueError: If an input stream is not seekable.
            PreprocessorError
        """

        if isinstance(istream, TextIOWrapper):
            istream_name = istream.name
        else:
            istream_name = '<stream>'

        try:
            for i, line in enumerate(istream, 1):
                if m := self._DIRECTIVE_RE.match(line):
                    prefix, directive, postfix = m.group(1, 2, 3)
                    if directive not in self.directives:
                        raise NoSuchDirective(directive, i, istream_name)
        finally:
            istream.seek(0)

    def process_stream(self,
                       istream: TextIOBase,
                       ostream: TextIOBase = sys.stdout) -> None:
        """Process input stream and write to output stream.

        Guarantees that no data will be written into the output stream,
        if an exception occurs.

        Args:
            istream: Input stream.
            ostream: Output stream.

        Raises:
            PreprocessorError
        """

        self.check_stream(istream)

        for i, line in enumerate(istream, 1):
            if m := self._DIRECTIVE_RE.match(line):
                prefix, directive, postfix = m.group(1, 2, 3)
                content = self.directives[directive]
                self._insert(content, ostream, prefix, postfix)
            else:
                ostream.write(line)


class FilePreprocessor(Preprocessor):
    """Creates source code files, replacing directives in skeleton files."""

    def __init__(self, directives):
        super().__init__(directives)
        self._errors: list[PreprocessorError] = []

    @overload
    def process(self, files: dict[Path | str, Optional[Path | str]]):
        ...

    @overload
    def process(self, files: Iterable[tuple[Path | str, Optional[Path | str]]]):
        ...

    def process(self, files):
        """Create source files from skeleton files.

        `files` argument may be either a dict[InputFile, OutputFile] or
        a sequence[tuple[InputFile, OutputFile]]. OutputFile will be created
        from the corresponding InputFile. If OutputFile is None, then
        its path and filename will be constructed from the InputFile.

        If OutputFile is None, then its name will be the same as
        InputFile's file name, but if the InputFile has '.skel' extension
        at the end, OutputFile has not.

        Guarantees that no file will be created or rewritten if an
        exception occurs.

        Raises all exceptions that built-in `open` function raises.

        Args:
            files

        Raises:
            NoSuchDirective
        """

        if isinstance(files, dict):
            files = files.items()

        for input_file, output_file in files:
            input_file = Path(input_file)

            if output_file is None:
                output_path = input_file.parent
                name = input_file.name
                if (idx := name.find('.skel')) != -1 and idx + 5 == len(name):
                    name = name[:idx]
                output_file = Path(output_path, name)
            else:
                output_file = Path(output_file)

            try:
                if self._errors:
                    self.check_file(input_file)
                else:
                    self.process_file(input_file, output_file)
            except PreprocessorError as exc:
                self._errors.append(exc)

        if self._errors:
            raise FilePreprocessorError(*self._errors)

    def check_file(self, input_file: Path | str):
        """Check skeleton file for errors.

        Raises all exceptions that built-in `open` function raises.

        Args:
            input_file: A path to an output file.

        Raises:
            PreprocessorError
        """

        with open(input_file, 'r', encoding=self.ENCODING) as fin:
            self.check_stream(fin)

    def process_file(self, input_file: Path | str, output_file: Path | str):
        """Create source code file from skeleton file.

        Guarantees that no file will be created or rewritten if an
        exception occurs.

        Raises all exceptions that built-in `open` function raises.

        Args:
            input_file: A path to an input file.
            output_file: A path to an output file.

        Raises:
            PreprocessorError
        """

        with (open(input_file, 'r', encoding=self.ENCODING) as fin,
              open(output_file, 'w', encoding=self.ENCODING) as fout):
            self.process_stream(fin, fout)
