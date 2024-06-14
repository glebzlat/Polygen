from io import TextIOBase
from abc import abstractmethod
from contextlib import contextmanager

from .node import Grammar


class GeneratorError(Exception):
    pass


class GeneratorBase:
    def __init__(self, stream: TextIOBase):
        self._indentation = ''
        self._indent_level = 0
        self._stream = stream
        self._put_impl = self._put_line

    def put(self, *args, newline=True, indent=True):
        self._put_impl(args, newline, indent)

    def _put_line(self, args, newline, indent):
        if indent:
            print(end=self._indentation, file=self._stream)
        print(*args, end='', file=self._stream)
        if newline:
            print(file=self._stream)

    @contextmanager
    def indent(self, level: int = 1):
        save = self._indentation
        try:
            self._indentation += '    ' * level
            self._indent_level += level
            yield
        finally:
            self._indentation = save
            self._indent_level -= level

    def emptyline(self):
        self.put(indent=False)

    @contextmanager
    def function_call(self, name: str, newline=False):
        parts = []

        def _put_arg(self, *args, newline=True, indent=True):
            parts.extend(args)

        put_save = self._put_impl
        self._put_impl = _put_arg

        try:
            yield
        finally:
            self._put_impl = put_save

        self.put(f"{name}(", newline=False, indent=False)
        self.put(', '.join(str(i) for i in parts), newline=False, indent=False)
        self.put(")", newline=newline, indent=False)

    @contextmanager
    def enclose(self, start: str, end: str, *, newline=False, indent=False):
        self.put(start, newline=False, indent=indent)
        yield
        self.put(end, indent=False, newline=newline)

    @abstractmethod
    def generate(self, grammar: Grammar):
        raise NotImplementedError
