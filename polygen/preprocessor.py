import re
import sys

from io import StringIO
from typing import TextIO


class PreprocessorError(Exception):
    pass


class Preprocessor:
    """Creates a source code from the skeleton file, substituting directives.

    Directives in the skeleton files are single words, preceded by two percent
    symbols '%'. Directive may be indented with whitespace, in this case
    all lines of inserted content will be indented using the same indentation,
    as the directive.

    Lines, that do not contain valid directives, will be written without
    changes.

    Directive can not be preceded by anything, except whitespace.

    This will not work:

    ```
    # %% directive
    return %% return_value
    ```
    """

    _DIRECTIVE_RE = re.compile(r'\A(\s*)%% +(\w+) *(?:\n\r?)?\Z')
    _NEWLINE_RE = re.compile(r'\A\n\r?\Z')

    def __init__(self, directives: dict[str, str | TextIO]):
        """Initialize Preprocessor.

        Arguments:
            directives: A mapping from the directive name to its substitution.
        """
        self.directives = directives

    def _insert(self,
                content: str | TextIO,
                ostream: TextIO,
                indent: str) -> None:
        istream = StringIO(content) if isinstance(content, str) else content

        for line in istream:
            if self._NEWLINE_RE.match(line):
                ostream.write(line)
            else:
                ostream.write(indent + line)

    def process(self,
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
                indent, directive = m.group(1, 2)
                content = self.directives.get(directive)
                if content is None:
                    raise PreprocessorError
                self._insert(content, ostream, indent)
            else:
                ostream.write(line)
