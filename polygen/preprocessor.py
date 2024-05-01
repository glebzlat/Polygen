import re
import sys

from io import StringIO, TextIOBase


class PreprocessorError(Exception):
    pass


class Preprocessor:
    _DIRECTIVE_RE = re.compile(r'\A(\s*)%% +(\w+) *(?:\n\r?)?\Z')
    _NEWLINE_RE = re.compile(r'\A\n\r?\Z')

    def __init__(self, directives: dict[str, str | TextIOBase]):
        self.directives = directives

    def _insert(self,
                content: str | TextIOBase,
                ostream: TextIOBase,
                indent: str):
        istream = StringIO(content) if isinstance(content, str) else content

        for line in istream:
            if self._NEWLINE_RE.match(line):
                ostream.write(line)
            else:
                ostream.write(indent + line)

    def process(self,
                istream: str | TextIOBase,
                ostream: TextIOBase = sys.stdout):
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
