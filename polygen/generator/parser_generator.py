from io import TextIOBase
from abc import abstractmethod
from contextlib import contextmanager

from ..grammar.node import Grammar


class GeneratorError(Exception):
    pass


class ParserGenerator:
    def __init__(self, stream: TextIOBase):
        self._indentation = ''
        self._indent_level = 0
        self._stream = stream

    def _put(self, *args, newline=True, indent=True):
        if indent:
            print(end=self._indentation, file=self._stream)
        print(*args, end='', file=self._stream)
        if newline:
            print(file=self._stream)

    @contextmanager
    def _indent(self, level: int = 1):
        save = self._indentation
        try:
            self._indentation += '    ' * level
            self._indent_level += level
            yield
        finally:
            self._indentation = save
            self._indent_level -= level

    def _emptyline(self):
        self._put(indent=False)

    @abstractmethod
    def generate(self, grammar: Grammar):
        raise NotImplementedError
