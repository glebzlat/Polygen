from __future__ import annotations
import io


class Reader:
    """Read the file and produces a stream of characters.

    Cannot work with Unicode, except UTF-8.
    """

    def __init__(self, stream: str | io.IOBase, bufsize: int = 4096) -> None:
        self.buffer = ""
        self.stream = None
        self.name = None
        self.bufsize = bufsize
        self.eof = False
        self.pointer = 0
        self.line = 1
        self.column = 0

        if isinstance(stream, str):
            self.name = "<unicode string>"
            self.buffer = stream + '\0'
        elif isinstance(stream, io.IOBase):
            self.name = getattr(stream, 'name', '<file>')
            self.stream = stream
            self.eof = False

            if not stream.readable():
                with_name = f": {self.name}" if self.name else ""
                raise ValueError("stream must be readable" + with_name)

    def __iter__(self) -> Reader:
        return self

    def __next__(self) -> str:
        try:
            char = self.buffer[self.pointer]
        except IndexError:
            if self.stream:
                self._update()
            try:
                char = self.buffer[self.pointer]
            except IndexError:
                self.eof = True
                raise StopIteration
        if char in '\r\n':
            self.line += 1
            self.column = 0
        elif char == '\0':
            pass  # Prevent column from incrementing by the last '\0' char.
        else:
            self.column += 1
        self.pointer += 1
        return char

    def _update(self, length: int = 1) -> None:
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
                self.buffer += '\0'
                break
