import typing
import re

from .parser import Parser
from .node import (
    Rule,
    Range,
    Expression,
    Sequence,
    Identifier,
    Literal,
    Class,
    Predicate,
    Quantifier,
    Repetition,
    Char
)


class GrammarParser(Parser):
    # Naming style:
    #   - parsing functions have exact names of corresponding grammar
    #     rules, but prefixed with '_'
    #   - private functions names are prefixed with '_'
    #   - private members are prefixed with '__'
    #   - regular expression variables are all uppercase suffixed with '_RE'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__IDENTSTART_RE = re.compile(r'[a-zA-Z_]')
        self.__IDENTCONT_RE = re.compile(r'[a-zA-Z0-9_]')
        self.__HEXDIGIT_RE = re.compile(r'[0-9a-fA-F]')

    def parse(self) -> list[Rule] | None:
        return self._Grammar()

    def _Grammar(self) -> list[Rule] | None:
        if self._Spacing():
            if d := self._Definition():
                defs = [d]
                while d := self._Definition():
                    defs.append(d)
                if self._EndOfFile():
                    return defs

    def _Definition(self) -> Rule | None:
        if i := self._Identifier():
            if self._LEFTARROW():
                if e := self._Expression():
                    return Rule(i, e)

    def _Expression(self) -> Expression | None:
        if s := self._Sequence():
            seqs = [s]
            while self._SLASH() and (s := self._Sequence()):
                seqs.append(s)
            return Expression(*seqs)

    def _Sequence(self) -> Sequence | None:
        prefixes = []
        while p := self._Prefix():
            prefixes.append(p)
        return Sequence(*prefixes)

    def _Prefix(self) -> tuple[Predicate, tuple] | None:
        if self._AND():
            p = Predicate(Predicate.AND)
        elif self._NOT():
            p = Predicate(Predicate.NOT)
        else:
            p = None
        if s := self._Suffix():
            return (p, s)  # (Predicate, (Primary, Quantifier))

    def _Suffix(self) -> tuple | None:
        if p := self._Primary():
            if self._QUESTION():
                q = Quantifier(Quantifier.OPTIONAL)
            elif self._STAR():
                q = Quantifier(Quantifier.ZERO_OR_MORE)
            elif self._PLUS():
                q = Quantifier(Quantifier.ONE_OR_MORE)
            elif q := self._Repetition():
                q = Quantifier(q)
            else:
                q = None
            return (p, q)  # (Primary, Quantifier)

    def _Primary(self) -> Identifier | Expression | None:
        pos = self._mark()
        if i := self._Identifier():
            if self._LEFTARROW():
                self._reset(pos)
                return
            return i
        if self._OPEN():
            if e := self._Expression():
                if self._CLOSE():
                    return e
        return self._Literal() or self._Class() or self._DOT()

    def _Identifier(self) -> Identifier | None:
        if c := self._IdentStart():
            chars = [c]
            while c := self._IdentCont():
                chars.append(c)
            if self._Spacing():
                return Identifier(''.join(chars))

    def _IdentStart(self) -> str | None:
        pos = self._mark()
        ch = self._get_char()
        if self.__IDENTSTART_RE.match(ch):
            return ch
        self._reset(pos)

    def _IdentCont(self) -> str | None:
        pos = self._mark()
        ch = self._get_char()
        if self.__IDENTCONT_RE.match(ch):
            return ch
        self._reset(pos)

    def _Literal(self) -> Literal | None:
        pos = self._mark()
        if (q := self._expect('\'')) or (q := self._expect('\"')):
            chars = []
            while self._peek_char() != q and (c := self._Char()):
                chars.append(c)
            if self._expect(q):
                if self._Spacing():
                    return Literal(*chars)
        self._reset(pos)

    def _Class(self):
        pos = self._mark()
        if self._expect('['):
            ranges = []
            while self._peek_char() != ']' and (r := self._Range()):
                ranges.append(r)
            if self._expect(']'):
                if self._Spacing():
                    return Class(*ranges)
        self._reset(pos)

    def _Range(self) -> Range | None:
        if beg := self._Char():
            pos = self._mark()
            if self._expect('-'):
                if end := self._Char():
                    return Range(beg, end)
            self._reset(pos)
            return Range(beg)

    __CHR_MAP = {
        'n': Char('\n'),
        'r': Char('\r'),
        't': Char('\t'),
        '\'': Char('\''),
        '\"': Char('\"'),
        '[': Char('['),
        ']': Char(']'),
        '\\': Char('\\')
    }

    def _Char(self) -> str | Char | None:
        pos = self._mark()
        if self._expect('\\'):
            ch = self._get_char()

            # '\\' [nrt'"\[\]\\]
            if char := self.__CHR_MAP.get(ch):
                return char
            else:
                octal_digits = set('01234567')

                # '\\' [0-2][0-7][0-7]
                if ch in '012':
                    digits = [ch]
                    if (ch := self._get_char()) and ch in octal_digits:
                        digits.append(ch)
                        if (ch := self._get_char()) and ch in octal_digits:
                            digits.append(ch)
                            n = int(''.join(digits), base=8)
                            return Char(n)

                # '\\' [0-7][0-7]?
                elif ch in octal_digits:
                    digits = [ch]
                    if (ch := self._get_char()) and ch in octal_digits:
                        digits.append(ch)
                    n = int(''.join(digits), base=8)
                    return Char(n)

                # '\\u' HexDigit{4}
                elif ch == 'u':
                    digits, count = [], 0
                    while d := self._HexDigit():
                        digits.append(d)
                        count += 1
                    if count == 4:
                        n = int(''.join(digits), base=16)
                        return Char(n)

        elif (ch := self._get_char()) and ch not in '\\\0':
            return Char(ord(ch))
        self._reset(pos)

    def _Repetition(self) -> Repetition | None:
        pos = self._mark()
        if self._expect('{'):
            if beg := self._Number():
                pos1 = self._mark()
                if self._expect(','):
                    if end := self._Number():
                        if self._expect('}'):
                            return Repetition(beg, end)
                self._reset(pos1)
                if self._expect('}'):
                    if self._Spacing():
                        return Repetition(beg)
        self._reset(pos)

    def _Number(self) -> str | None:
        pos = self._mark()
        if (c := self._get_char()) and c.isdigit():
            chars = [c]
            pos1 = self._mark()
            while (c := self._get_char()) and c.isdigit():
                chars.append(c)
                pos1 = self._mark()
            self._reset(pos1)
            return ''.join(chars)
        self._reset(pos)

    def _HexDigit(self) -> str | None:
        pos = self._mark()
        if (c := self._get_char()) and self.__HEXDIGIT_RE.match(c):
            return c
        self._reset(pos)

    def _LEFTARROW(self) -> str | None:
        pos = self._mark()
        if c1 := self._expect('<'):
            if c2 := self._expect('-'):
                if self._Spacing():
                    return c1 + c2
        self._reset(pos)

    def _SLASH(self) -> str | None:
        pos = self._mark()
        if s := self._expect('/'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _AND(self) -> str | None:
        pos = self._mark()
        if s := self._expect('&'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _NOT(self) -> str | None:
        pos = self._mark()
        if s := self._expect('!'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _QUESTION(self) -> str | None:
        pos = self._mark()
        if s := self._expect('?'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _STAR(self) -> str | None:
        pos = self._mark()
        if s := self._expect('*'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _PLUS(self) -> str | None:
        pos = self._mark()
        if s := self._expect('+'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _OPEN(self) -> str | None:
        pos = self._mark()
        if s := self._expect('('):
            if self._Spacing():
                return s
        self._reset(pos)

    def _CLOSE(self) -> str | None:
        pos = self._mark()
        if s := self._expect(')'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _DOT(self) -> str | None:
        pos = self._mark()
        if s := self._expect('.'):
            if self._Spacing():
                return s
        self._reset(pos)

    def _Spacing(self) -> typing.Literal[True]:
        while self._Space() or self._Comment():
            pass
        return True

    def _Comment(self) -> str | None:
        pos = self._mark()
        if c := self._expect('#'):
            chars = [c]
            while not self._EndOfLine() and (c := self._get_char()):
                chars.append(c)
            return ''.join(chars)
        self._reset(pos)

    def _Space(self) -> str | None:
        pos = self._mark()
        if (c := (self._expect(' ')) or
                self._expect('\t') or self._EndOfLine()):
            return c
        self._reset(pos)

    def _EndOfLine(self) -> str | None:
        pos = self._mark()
        if c1 := self._expect('\r'):
            pos1 = self._mark()
            if c2 := self._expect('\n'):
                return c1 + c2
            self._reset(pos1)
            return c1
        elif c := self._expect('\n'):
            return c
        self._reset(pos)

    def _EndOfFile(self) -> typing.Literal[True] | None:
        pos = self._mark()
        if self._get_char() == '\0':
            return True
        self._reset(pos)
