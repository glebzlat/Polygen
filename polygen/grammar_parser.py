from typing import Optional, Literal
import re

from .parser import Parser
from .node import (
    Grammar,
    Expression,
    Rule,
    Identifier,
    Range,
    Alt,
    Part,
    AnyChar,
    String as LiteralNode,
    Class,
    Not,
    And,
    PredicateType,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    QuantifierType,
    Repetition,
    Char
)

PrimaryType = Optional[
    Identifier | Expression | LiteralNode | Class | Char | AnyChar]
SuffixType = Optional[
    tuple[
        Optional[
            Identifier | Expression | LiteralNode | Class | AnyChar],
        Optional[QuantifierType]
    ]
]


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

    def parse(self) -> Optional[Grammar]:
        return self._Grammar()

    def _Grammar(self) -> Optional[Grammar]:
        if self._Spacing():
            if d := self._Definition():
                rules = [d]
                while d := self._Definition():
                    rules.append(d)
                if self._EndOfFile():
                    return Grammar(*rules)
        return None

    def _Definition(self) -> Optional[Rule]:
        directives = []
        while d := self._Directive():
            directives.append(d)

        if i := self._Identifier():
            if self._LEFTARROW():
                if e := self._Expression():
                    return Rule(i, e, directives=directives)
        return None

    def _Directive(self) -> Optional[str]:
        if self._AT():
            if id := self._DirName():
                if self._Spacing():
                    return id.string
        return None

    def _DirName(self) -> Optional[Identifier]:
        if i := self._Identifier():
            return i
        return None

    def _Expression(self) -> Optional[Expression]:
        if s := self._Sequence():
            seqs = [s]
            while self._SLASH() and (s := self._Sequence()):
                seqs.append(s)
            return Expression(*seqs)
        return None

    def _Sequence(self) -> Optional[Alt]:
        prefixes = []
        while p := self._Prefix():
            prefixes.append(p)
        meta = self._MetaRule()
        return Alt(*prefixes, metarule=meta)

    def _Prefix(self) -> Optional[Part]:
        meta, p = None, None
        if meta := self._MetaName():
            pass
        elif p := self._AND():
            pass
        elif p := self._NOT():
            pass
        if s := self._Suffix():
            return Part(pred=p, prime=s[0], quant=s[1], metaname=meta)
        return None

    def _Suffix(self) -> SuffixType:
        if p := self._Primary():
            q = (self._QUESTION() or self._STAR() or
                 self._PLUS() or self._Repetition())
            return (p, q)  # (Primary, QuantifierType)
        return None

    def _Primary(self) -> PrimaryType:
        pos = self._mark()
        if i := self._Identifier():
            if self._LEFTARROW():
                self._reset(pos)
                return None
            return i
        if self._OPEN():
            if e := self._Expression():
                if self._CLOSE():
                    return e
        return self._Literal() or self._Class() or self._DOT()

    def _MetaName(self) -> Optional[str]:
        pos = self._mark()
        if i := self._Identifier():
            if self._EQUAL():
                return i.string
        self._reset(pos)
        return None

    def _MetaRule(self) -> Optional[str]:
        pos = self._mark()
        if self._PERCENT():
            if i := self._Identifier():
                return i.string
        self._reset(pos)
        return None

    def _Identifier(self) -> Optional[Identifier]:
        if c := self._IdentStart():
            chars = [c]
            while c := self._IdentCont():
                chars.append(c)
            if self._Spacing():
                return Identifier(''.join(chars))
        return None

    def _IdentStart(self) -> Optional[str]:
        pos = self._mark()
        ch = self._get_char()
        if self.__IDENTSTART_RE.match(ch):
            return ch
        self._reset(pos)
        return None

    def _IdentCont(self) -> Optional[str]:
        pos = self._mark()
        ch = self._get_char()
        if self.__IDENTCONT_RE.match(ch):
            return ch
        self._reset(pos)
        return None

    def _Literal(self) -> Optional[LiteralNode | Char]:
        pos = self._mark()
        if (q := self._expect('\'')) or (q := self._expect('\"')):
            chars = []
            while self._peek_char() != q and (c := self._Char()):
                chars.append(c)
            if self._expect(q):
                if self._Spacing():
                    if len(chars) == 1:
                        return chars[0]
                    return LiteralNode(*chars)
        self._reset(pos)
        return None

    def _Class(self) -> Optional[Class]:
        pos = self._mark()
        if self._expect('['):
            ranges = []
            while self._peek_char() != ']' and (r := self._Range()):
                ranges.append(r)
            if self._expect(']'):
                if self._Spacing():
                    return Class(*ranges)
        self._reset(pos)
        return None

    def _Range(self) -> Optional[Range]:
        if beg := self._Char():
            pos = self._mark()
            if self._expect('-'):
                if end := self._Char():
                    return Range(beg, end)
            self._reset(pos)
            return Range(beg)
        return None

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

    def _Char(self) -> Optional[Char]:
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
        return None

    def _Repetition(self) -> Optional[Repetition]:
        pos = self._mark()
        if self._expect('{'):
            if beg := self._Number():
                pos1 = self._mark()
                if self._expect(','):
                    if end := self._Number():
                        if self._expect('}'):
                            return Repetition(int(beg), int(end))
                self._reset(pos1)
                if self._expect('}'):
                    if self._Spacing():
                        return Repetition(int(beg))
        self._reset(pos)
        return None

    def _Number(self) -> Optional[str]:
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
        return None

    def _HexDigit(self) -> Optional[str]:
        pos = self._mark()
        if (c := self._get_char()) and self.__HEXDIGIT_RE.match(c):
            return c
        self._reset(pos)
        return None

    def _LEFTARROW(self) -> Optional[str]:
        pos = self._mark()
        if c1 := self._expect('<'):
            if c2 := self._expect('-'):
                if self._Spacing():
                    return c1 + c2
        self._reset(pos)
        return None

    def _SLASH(self) -> Optional[str]:
        pos = self._mark()
        if s := self._expect('/'):
            if self._Spacing():
                return s
        self._reset(pos)
        return None

    def _AND(self) -> Optional[PredicateType]:
        pos = self._mark()
        if self._expect('&'):
            if self._Spacing():
                return And()
        self._reset(pos)
        return None

    def _NOT(self) -> Optional[PredicateType]:
        pos = self._mark()
        if self._expect('!'):
            if self._Spacing():
                return Not()
        self._reset(pos)
        return None

    def _QUESTION(self) -> Optional[QuantifierType]:
        pos = self._mark()
        if self._expect('?'):
            if self._Spacing():
                return ZeroOrOne()
        self._reset(pos)
        return None

    def _STAR(self) -> Optional[QuantifierType]:
        pos = self._mark()
        if self._expect('*'):
            if self._Spacing():
                return ZeroOrMore()
        self._reset(pos)
        return None

    def _PLUS(self) -> Optional[QuantifierType]:
        pos = self._mark()
        if self._expect('+'):
            if self._Spacing():
                return OneOrMore()
        self._reset(pos)
        return None

    def _OPEN(self) -> Optional[str]:
        pos = self._mark()
        if s := self._expect('('):
            if self._Spacing():
                return s
        self._reset(pos)
        return None

    def _CLOSE(self) -> Optional[str]:
        pos = self._mark()
        if s := self._expect(')'):
            if self._Spacing():
                return s
        self._reset(pos)
        return None

    def _DOT(self) -> Optional[AnyChar]:
        pos = self._mark()
        if self._expect('.'):
            if self._Spacing():
                return AnyChar()
        self._reset(pos)
        return None

    def _AT(self) -> Optional[str]:
        pos = self._mark()
        if s := self._expect('@'):
            if self._Spacing():
                return s
        self._reset(pos)
        return None

    def _EQUAL(self) -> Optional[str]:
        pos = self._mark()
        if s := self._expect('='):
            if self._Spacing():
                return s
        self._reset(pos)
        return None

    def _PERCENT(self) -> Optional[str]:
        pos = self._mark()
        if s := self._expect('%'):
            if self._Spacing():
                return s
        self._reset(pos)
        return None

    def _Spacing(self) -> Literal[True]:
        while self._Space() or self._Comment():
            pass
        return True
        return None

    def _Comment(self) -> Optional[str]:
        pos = self._mark()
        if c := self._expect('#'):
            chars = [c]
            while not self._EndOfLine() and (c := self._get_char()):
                chars.append(c)
            return ''.join(chars)
        self._reset(pos)
        return None

    def _Space(self) -> Optional[str]:
        pos = self._mark()
        if (c := (self._expect(' ')) or
                self._expect('\t') or self._EndOfLine()):
            return c
        self._reset(pos)
        return None

    def _EndOfLine(self) -> Optional[str]:
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
        return None

    def _EndOfFile(self) -> Optional[Literal[True]]:
        pos = self._mark()
        if self._get_char() == '\0':
            return True
        self._reset(pos)
        return None
