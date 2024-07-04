from __future__ import annotations

import io

from typing import Optional


class Token(str):
    def __new__(cls,
                value: str,
                line: int,
                start: int,
                end: int,
                filename: Optional[str] = None):
        self = super().__new__(cls, value)
        self.value = value
        self.line = line
        self.start = start
        self.end = end
        self.filename = filename
        return self

    def __repr__(self):
        return f"Token({self.value!r}, {self.line}, {self.start}, {self.end})"

    def __str__(self):
        return repr(self.value)


class Reader:
    """
    Reads the file and produces a stream of characters.

    Reader supports strings and UTF-8 encoded streams only.
    """

    def __init__(self, stream: str | io.TextIOBase, bufsize=4096):
        self.buffer = ""
        self.stream = None
        self.name = None
        self.bufsize = bufsize
        self.eof = False
        self.pointer = 0
        self.line = 1
        self.column = 0

        if isinstance(stream, str):
            self.name = "<string>"
            self.buffer = stream
        elif isinstance(stream, io.IOBase):
            self.name = getattr(stream, 'name', '<stream>')
            self.stream = stream
            self.eof = False

            if not stream.readable():
                raise ValueError(f"stream must be readable: {self.name}")

    def __iter__(self) -> Reader:
        return self

    def __next__(self) -> Token:
        try:
            char = self.buffer[self.pointer]
        except IndexError:
            if self.stream:
                self.update()
            try:
                char = self.buffer[self.pointer]
            except IndexError:
                self.eof = True
                raise StopIteration
        if char in '\r\n':
            self.line += 1
            self.column = 0
        else:
            self.column += 1
        self.pointer += 1
        return Token(char, self.line, self.pointer - 1, self.pointer, self.name)

    def update(self, length: int = 1) -> None:
        assert self.stream
        if self.eof:
            return
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        while len(self.buffer) < length:
            data = self.stream.read(self.bufsize)
            if data:
                self.buffer += data
            else:
                self.eof = True
                break


