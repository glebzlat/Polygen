import re
import sys

from io import StringIO
from typing import TextIO, Iterable, Optional, overload
from pathlib import Path


class PreprocessorError(Exception):
    pass


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

    def process_stream(self,
                       istream: str | TextIO,
                       ostream: TextIO = sys.stdout) -> None:
        """Process input stream and write to output stream.

        Args:
            istream: Input stream.
            ostream: Output stream.

        Raises:
            PreprocessorError
        """
        istream = StringIO(istream) if isinstance(istream, str) else istream

        for line in istream:
            if m := self._DIRECTIVE_RE.match(line):
                prefix, directive, postfix = m.group(1, 2, 3)
                content = self.directives.get(directive)
                if content is None:
                    raise PreprocessorError(f"{directive!r} is None")
                self._insert(content, ostream, prefix, postfix)
            else:
                ostream.write(line)


class FilePreprocessor(Preprocessor):
    """Creates source code files, replacing directives in skeleton files."""

    @overload
    def process(self, files: dict[Path | str, Optional[Path | str]]):
        ...

    @overload
    def process(self, files: Iterable[tuple[Path | str, Optional[Path | str]]]):
        ...

    def process(self, files):
        """Create source files from skeleton files.

        Args:
            files: A sequence of tuple[InputFile, OutputFile],
                where the OutputFile will be created from the corresponding
                InputFile. If OutputFile is None, then the path for newly
                created file will be taken from InputFile. In this case the
                filename will be created from InputFile's filename with the
                '.skel' part removed (if it is appeared and appeared at the
                end of the filename).
        """

        for input_file, output_file in files:
            input_file = Path(input_file)

            if output_file is None:
                output_path = input_file.parent
                output_filename = input_file.name.rstrip('.skel')
                output_file = Path(output_path, output_filename)
            else:
                output_file = Path(output_file)

            self.process_file(input_file, output_file)

    def process_file(self, input_file: Path | str, output_file: Path | str):
        """Create source code file from skeleton file."""

        with (open(input_file, 'r', encoding=self.ENCODING) as fin,
              open(output_file, 'w', encoding=self.ENCODING) as fout):
            self.process_stream(fin, fout)
