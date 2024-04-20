from .reader import Reader


class Parser:
    def __init__(self, reader: Reader):
        self.reader = reader
        self.chars = []
        self.pos = 0

    def _mark(self) -> int:
        return self.pos

    def _reset(self, pos: int):
        self.pos = pos

    def _get_char(self) -> str:
        char = self._peek_char()
        self.pos += 1
        return char

    def _peek_char(self) -> str:
        if self.pos == len(self.chars):
            self.chars.append(next(self.reader))
        return self.chars[self.pos]

    def _expect(self, arg: str) -> str | None:
        ch = self._peek_char()
        if ch == arg:
            return self._get_char()
        return None
