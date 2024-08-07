# This is automatically generated code, do not edit.
# Generated by Polygen 0.1.0


from __future__ import annotations

import io

from functools import wraps
from typing import Optional, Union, Any, Tuple, List, Callable


from polygen.node import (
    Grammar,
    Rule,
    MetaRef,
    MetaRule,
    Expr,
    Alt,
    NamedItem,
    Id,
    String,
    Char,
    AnyChar,
    Class,
    Range,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    And,
    Not
)


__all__ = ["Token", "Reader", "Parser"]


class Token(str):
    def __new__(cls,
                value: str,
                line: int,
                start: int,
                end: int,
                filename: Optional[str] = None):
        self = super().__new__(cls, value)
        self.line = line
        self.start = start
        self.end = end
        self.filename = filename
        return self

    @property
    def value(self):
        return str(self)

    def __repr__(self):
        return f"Token({self.value!r}, {self.line}, {self.start}, {self.end})"


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
        tok = Token(char, self.line, self.column, self.column + 1, self.name)
        if char in '\r\n':
            self.line += 1
            self.column = 0
        else:
            self.column += 1
        self.pointer += 1
        return tok

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


class _MemoEntry:
    def __init__(self, value: Union[str, Any], pos: int):
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"MemoEntry({self.value}, {self.pos})"

    def __str__(self):
        return repr(self)


def _memoize(fn):

    @wraps(fn)
    def wrapper(self, *args):
        pos = self._mark()
        key = (fn, args, pos)
        memo = self._memos.get(key)
        if memo is None:
            self._memos[key] = memo = _MemoEntry(fn(self, *args), self._mark())
        else:
            self._reset(memo.pos)
        return memo.value

    return wrapper


def _memoize_lr(fn):

    context = fn.__name__

    @wraps(fn)
    def wrapper(self, *args):
        pos = self._mark()
        key = (fn, args, pos)
        memo = self._memos.get(key)

        # Memo entry can be created during the seed planting and can be
        # wrong for the given position, so treat entry with None result
        # as no memo entry.
        if memo is None or memo.result is None:
            seeds, growers = self._grow_rules[context]

            self._memos[key] = memo = _MemoEntry(None, pos)

            # First plant the seed
            result = None
            for seed in seeds:
                result = seed()
                if result is not None:
                    break
            if result is None:
                return None
            memo.result, memo.pos = result, self._pos

            # Then grow the LR, repeatedly calling recursive alternatives
            # until there is no improvement
            while True:
                self._pos = pos
                for alt in growers:
                    # Ordered choice
                    result = alt()
                    if result is not None:
                        break
                    self._pos = pos
                if self._pos <= memo.pos:
                    # No improvement
                    self._pos = memo.pos
                    return memo.result
                memo.result = result
                memo.pos = self._pos

        else:
            self._pos = memo.pos
            return memo.result

    return wrapper


class Parser:

    def __init__(self, reader: Reader, actions=None):
        self._memos = {}

        self._reader = reader
        self._tokens: List[Token] = []
        self._pos = 0

        self._grow_rules: Dict[str, Tuple[List[Callable], List[Callable]]] = {
            
        }

    @_memoize
    def _expectc(self, char: Optional[str] = None) -> Optional[Token]:
        if tok := self._peek_token():
            if char is None or tok.value == char:
                self._pos += 1
                return tok
        return None

    @_memoize
    def _expects(self, string: str) -> Optional[Token]:
        pos = self._mark()
        for c in string:
            tok = self._peek_token()
            if tok is None or c != tok.value:
                self._reset(pos)
                return None
            self._pos += 1
        reader = self._reader
        line, start, end, filename = reader.line, pos, self._pos, reader.name
        return Token(string, line, start, end, filename)

    def _lookahead(self, positive, fn, *args) -> Optional[list]:
        pos = self._mark()
        ok = fn(*args) is not None
        self._reset(pos)
        if ok == positive:
            return []
        return None

    def _loop(self, nonempty, fn, *args) -> Optional[List[Token]]:
        pos = lastpos = self._mark()
        tokens = []
        while (tok := fn(*args)) is not None and self._mark() > lastpos:
            tokens.append(tok)
            lastpos = self._mark()
        if len(tokens) >= nonempty:
            return tokens
        self._reset(pos)
        return None

    def _rep(self, beg, end, fn, *args) -> Optional[List[Token]]:
        end = beg if end is None else end
        pos = lastpos = self._mark()
        count = 0
        tokens = []
        while (tok := fn(*args)) is not None and self._mark() > lastpos:
            tokens.append(tok)
            lastpos = self._mark()
            count += 1
        if count >= beg and count <= end:
            return tokens
        self._reset(pos)
        return None

    def _ranges(self, *ranges) -> Optional[str]:
        token = self._peek_token()
        if token is None:
            return None
        value = token.value
        for beg, end in ranges:
            if value >= beg and value <= end:
                self._pos += 1
                return token

    def _maybe(self, fn, *args) -> Union[list, Token, Any]:
        result = fn(*args)
        return result if result is not None else []

    def _get_token(self) -> Optional[Token]:
        token = self._peek_token()
        self._pos += 1
        return token

    def _peek_token(self) -> Optional[Token]:
        if self._pos == len(self._tokens):
            self._tokens.append(next(self._reader, None))
        return self._tokens[self._pos]

    def _mark(self) -> int:
        return self._pos

    def _reset(self, pos: int):
        self._pos = pos

    def parse(self) -> Any:
        return self._Grammar()

    @_memoize
    def _Grammar(self):
        _begin_pos = self._mark()
        if (
            self._Spacing() is not None
            and (entity := self._loop(True, self._Entity)) is not None
            and (endoffile := self._EndOfFile()) is not None
        ):
            # Spacing Entity+ EndOfFile

            # Metarule: grammar_action
            rules = (r for r in entity if isinstance(r, Rule))
            metarules = (r for r in entity if isinstance(r, MetaRule))
            return Grammar(rules, metarules)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Entity(self):
        _begin_pos = self._mark()
        if ((definition := self._Definition()) is not None):
            # Definition
            return definition
        self._reset(_begin_pos)
        if ((metadef := self._MetaDef()) is not None):
            # MetaDef
            return metadef
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Definition(self):
        _begin_pos = self._mark()
        if (
            (directive := self._loop(False, self._Directive)) is not None
            and (identifier := self._Identifier()) is not None
            and self._LEFTARROW() is not None
            and (expression := self._Expression()) is not None
        ):
            # Directive* Identifier LEFTARROW Expression

            # Metarule: def_action
            ignore = "ignore" in directive
            entry = "entry" in directive
            return Rule(identifier, expression, ignore=ignore, entry=entry)
        self._reset(_begin_pos)
        if ((metadef := self._MetaDef()) is not None):
            # MetaDef
            return metadef
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Directive(self):
        _begin_pos = self._mark()
        if (
            self._AT() is not None
            and (dirname := self._DirName()) is not None
            and self._Spacing() is not None
        ):
            # AT DirName Spacing

            # Metarule: directive_action
            return dirname.value
        self._reset(_begin_pos)
        return None

    @_memoize
    def _DirName(self):
        _begin_pos = self._mark()
        if ((identifier := self._Identifier()) is not None):
            # Identifier
            return identifier
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Expression(self):
        # Nullable
        _begin_pos = self._mark()
        if (
            (sequence := self._Sequence()) is not None
            and (seqs := self._loop(False, self._Expression__GEN_1)) is not None
        ):
            # Nullable
            # Sequence Expression__GEN_1*

            # Metarule: expr_action
            return Expr((sequence, *seqs))
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Sequence(self):
        # Nullable
        _begin_pos = self._mark()
        if (
            (parts := self._loop(False, self._Prefix)) is not None
            and (m := self._maybe(self._MetaRule)) is not None
        ):
            # Nullable
            # Prefix* MetaRule?

            # Metarule: sequence_action
            m = m or None
            return Alt(parts, metarule=m)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Prefix(self):
        _begin_pos = self._mark()
        if (
            (metaname := self._maybe(self._MetaName)) is not None
            and (lookahead := self._maybe(self._Prefix__GEN_1)) is not None
            and (suffix := self._Suffix()) is not None
        ):
            # MetaName? Prefix__GEN_1? Suffix

            # Metarule: prefix_action
            obj = lookahead(suffix) if lookahead else suffix
            metaname = metaname or None
            return NamedItem(metaname, obj)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Suffix(self):
        _begin_pos = self._mark()
        if (
            (primary := self._Primary()) is not None
            and (q := self._maybe(self._Suffix__GEN_1)) is not None
        ):
            # Primary Suffix__GEN_1?

            # Metarule: suffix_action
            return q(primary) if q else primary
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Primary(self):
        _begin_pos = self._mark()
        if (
            (identifier := self._Identifier()) is not None
            and self._lookahead(False, self._LEFTARROW) is not None
        ):
            # Identifier !LEFTARROW
            return identifier
        self._reset(_begin_pos)
        if (
            self._OPEN() is not None
            and (expression := self._Expression()) is not None
            and self._CLOSE() is not None
        ):
            # OPEN Expression CLOSE
            return expression
        self._reset(_begin_pos)
        if ((literal := self._Literal()) is not None):
            # Literal
            return literal
        self._reset(_begin_pos)
        if ((_class := self._Class()) is not None):
            # Class
            return _class
        self._reset(_begin_pos)
        if ((dot := self._DOT()) is not None):
            # DOT
            return dot
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MetaName(self):
        _begin_pos = self._mark()
        if (
            (identifier := self._Identifier()) is not None
            and self._SEMI() is not None
        ):
            # Identifier SEMI
            return identifier
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MetaRule(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('$')) is not None
            and (body := self._MetaDefBody()) is not None
        ):
            # '$' MetaDefBody

            # Metarule: metarule_def_action
            return MetaRule(None, body)
        self._reset(_begin_pos)
        if (
            (_1 := self._expectc('$')) is not None
            and self._Spacing() is not None
            and (identifier := self._Identifier()) is not None
            and self._lookahead(False, self._expectc, '{') is not None
        ):
            # '$' Spacing Identifier !'{'

            # Metarule: metarule_ref_action
            return MetaRef(identifier)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MetaDef(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('$')) is not None
            and self._Spacing() is not None
            and (identifier := self._Identifier()) is not None
            and (expr := self._MetaDefBody()) is not None
        ):
            # '$' Spacing Identifier MetaDefBody

            # Metarule: metadef_action
            return MetaRule(identifier, expr)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MetaDefBody(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('{')) is not None
            and (expr := self._loop(False, self._MetaDefBody__GEN_2)) is not None
            and (_2 := self._expectc('}')) is not None
            and self._Spacing() is not None
        ):
            # '{' MetaDefBody__GEN_2* '}' Spacing

            # Metarule: metadef_body_action
            return ''.join(expr)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _EscCurClose(self):
        _begin_pos = self._mark()
        if ((str := self._expects("\\}")) is not None):
            # "\\}"

            # Metarule: esc_cur_close_action
            return '}'
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Identifier(self):
        _begin_pos = self._mark()
        if (
            (start := self._IdentStart()) is not None
            and (cont := self._loop(False, self._IdentCont)) is not None
            and self._Spacing() is not None
        ):
            # IdentStart IdentCont* Spacing

            # Metarule: ident_action
            return Id(''.join((start, *cont)))
        self._reset(_begin_pos)
        return None

    @_memoize
    def _IdentStart(self):
        _begin_pos = self._mark()
        if ((_1 := self._ranges(('a', 'z'), ('A', 'Z'), ('_', '_'))) is not None):
            # [a-zA-Z_]
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _IdentCont(self):
        _begin_pos = self._mark()
        if ((identstart := self._IdentStart()) is not None):
            # IdentStart
            return identstart
        self._reset(_begin_pos)
        if ((_1 := self._ranges(('0', '9'))) is not None):
            # [0-9]
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Literal(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._ranges(("'", "'"))) is not None
            and (chars := self._loop(False, self._Literal__GEN_1)) is not None
            and (_2 := self._ranges(("'", "'"))) is not None
            and self._Spacing() is not None
        ):
            # ['] Literal__GEN_1* ['] Spacing

            # Metarule: literal_action
            if len(chars) == 1:
                return chars[0]
            return String(chars)
        self._reset(_begin_pos)
        if (
            (_1 := self._ranges(('"', '"'))) is not None
            and (chars := self._loop(False, self._Literal__GEN_2)) is not None
            and (_2 := self._ranges(('"', '"'))) is not None
            and self._Spacing() is not None
        ):
            # ["] Literal__GEN_2* ["] Spacing

            # Metarule: literal_action
            if len(chars) == 1:
                return chars[0]
            return String(chars)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Class(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('[')) is not None
            and (ranges := self._loop(False, self._Class__GEN_1)) is not None
            and (_2 := self._expectc(']')) is not None
            and self._Spacing() is not None
        ):
            # '[' Class__GEN_1* ']' Spacing

            # Metarule: class_action
            return Class(ranges)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Range(self):
        _begin_pos = self._mark()
        if (
            (beg := self._Char()) is not None
            and (_1 := self._expectc('-')) is not None
            and self._lookahead(False, self._expectc, ']') is not None
            and (end := self._Char()) is not None
        ):
            # Char '-' !']' Char

            # Metarule: range_2_action
            return Range(beg, end)
        self._reset(_begin_pos)
        if ((beg := self._Char()) is not None):
            # Char

            # Metarule: range_1_action
            return Range(beg)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Char(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('\\')) is not None
            and (char := self._ranges(('n', 'n'), ('r', 'r'), ('t', 't'), ("'", "'"), ('"', '"'), ('[', '['), (']', ']'), ('\\', '\\'))) is not None
        ):
            # '\\' [nrt'"[]\\]

            # Metarule: esc_char_action
            chr_map = {
                'n': '\n',
                'r': '\r',
                't': '\t',
            }

            return Char(chr_map.get(char, char))
        self._reset(_begin_pos)
        if (
            (_1 := self._expectc('\\')) is not None
            and (char1 := self._ranges(('0', '2'))) is not None
            and (char2 := self._ranges(('0', '7'))) is not None
            and (char3 := self._ranges(('0', '7'))) is not None
        ):
            # '\\' [0-2] [0-7] [0-7]

            # Metarule: oct_char_action_1
            string = ''.join((char1, char2, char3))
            return Char(int(string, base=8))
        self._reset(_begin_pos)
        if (
            (_1 := self._expectc('\\')) is not None
            and (char1 := self._ranges(('0', '7'))) is not None
            and (char2 := self._maybe(self._ranges, ('0', '7'))) is not None
        ):
            # '\\' [0-7] [0-7]?

            # Metarule: oct_char_action_2
            char2 = char2 if isinstance(char2, str) else ''
            string = ''.join((char1, char2))
            return Char(int(string, base=8))
        self._reset(_begin_pos)
        if (
            (_1 := self._expects("\\u")) is not None
            and (chars := self._rep(4, None, self._HexDigit)) is not None
        ):
            # "\\u" HexDigit{4}

            # Metarule: unicode_char_action
            string = ''.join(chars)
            return Char(int(string, base=16))
        self._reset(_begin_pos)
        if (
            self._lookahead(False, self._expectc, '\\') is not None
            and (any := self._expectc()) is not None
        ):
            # !'\\' .

            # Metarule: any_char_action
            return Char(ord(any))
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Repetition(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('{')) is not None
            and (grp := self._Repetition__GEN_1()) is not None
            and (_2 := self._expectc('}')) is not None
            and self._Spacing() is not None
        ):
            # '{' Repetition__GEN_1 '}' Spacing

            # Metarule: rep_action
            beg, end = grp if isinstance(grp, list) else (grp, None)
            return lambda item: Repetition(item, beg, end)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Number(self):
        _begin_pos = self._mark()
        if ((chars := self._loop(True, self._ranges, ('0', '9'))) is not None):
            # [0-9]+

            # Metarule: number_action
            string = ''.join(chars)
            return int(string)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _HexDigit(self):
        _begin_pos = self._mark()
        if ((char := self._ranges(('a', 'f'), ('A', 'F'), ('0', '9'))) is not None):
            # [a-fA-F0-9]
            return char
        self._reset(_begin_pos)
        return None

    @_memoize
    def _LEFTARROW(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expects("<-")) is not None
            and self._Spacing() is not None
        ):
            # "<-" Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _SLASH(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('/')) is not None
            and self._Spacing() is not None
        ):
            # '/' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _AND(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('&')) is not None
            and self._Spacing() is not None
        ):
            # '&' Spacing

            # Metarule: and_action
            return And
        self._reset(_begin_pos)
        return None

    @_memoize
    def _NOT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('!')) is not None
            and self._Spacing() is not None
        ):
            # '!' Spacing

            # Metarule: not_action
            return Not
        self._reset(_begin_pos)
        return None

    @_memoize
    def _QUESTION(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('?')) is not None
            and self._Spacing() is not None
        ):
            # '?' Spacing

            # Metarule: optional_action
            return ZeroOrOne
        self._reset(_begin_pos)
        return None

    @_memoize
    def _STAR(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('*')) is not None
            and self._Spacing() is not None
        ):
            # '*' Spacing

            # Metarule: zero_or_more_action
            return ZeroOrMore
        self._reset(_begin_pos)
        return None

    @_memoize
    def _PLUS(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('+')) is not None
            and self._Spacing() is not None
        ):
            # '+' Spacing

            # Metarule: one_or_more_action
            return OneOrMore
        self._reset(_begin_pos)
        return None

    @_memoize
    def _OPEN(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('(')) is not None
            and self._Spacing() is not None
        ):
            # '(' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _CLOSE(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc(')')) is not None
            and self._Spacing() is not None
        ):
            # ')' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _DOT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('.')) is not None
            and self._Spacing() is not None
        ):
            # '.' Spacing

            # Metarule: dot_action
            return AnyChar()
        self._reset(_begin_pos)
        return None

    @_memoize
    def _AT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('@')) is not None
            and self._Spacing() is not None
        ):
            # '@' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _SEMI(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc(':')) is not None
            and self._Spacing() is not None
        ):
            # ':' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Spacing(self):
        # Nullable
        _begin_pos = self._mark()
        if ((_1 := self._loop(False, self._Spacing__GEN_1)) is not None):
            # Nullable
            # Spacing__GEN_1*
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Comment(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('#')) is not None
            and (_2 := self._loop(False, self._Comment__GEN_1)) is not None
            and (endofline := self._EndOfLine()) is not None
        ):
            # '#' Comment__GEN_1* EndOfLine
            return [_1, _2, endofline]
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Space(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc(' ')) is not None):
            # ' '
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\t')) is not None):
            # '\t'
            return _1
        self._reset(_begin_pos)
        if ((endofline := self._EndOfLine()) is not None):
            # EndOfLine
            return endofline
        self._reset(_begin_pos)
        return None

    @_memoize
    def _EndOfLine(self):
        _begin_pos = self._mark()
        if ((_1 := self._expects("\r\n")) is not None):
            # "\r\n"
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\n')) is not None):
            # '\n'
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\r')) is not None):
            # '\r'
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _EndOfFile(self):
        # Nullable
        _begin_pos = self._mark()
        if (self._lookahead(False, self._expectc) is not None):
            # Nullable
            # !.
            return []
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Expression__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._SLASH() is not None
            and (sequence := self._Sequence()) is not None
        ):
            # SLASH Sequence
            return sequence
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Prefix__GEN_1(self):
        _begin_pos = self._mark()
        if ((_and := self._AND()) is not None):
            # AND
            return _and
        self._reset(_begin_pos)
        if ((_not := self._NOT()) is not None):
            # NOT
            return _not
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Suffix__GEN_1(self):
        _begin_pos = self._mark()
        if ((question := self._QUESTION()) is not None):
            # QUESTION
            return question
        self._reset(_begin_pos)
        if ((star := self._STAR()) is not None):
            # STAR
            return star
        self._reset(_begin_pos)
        if ((plus := self._PLUS()) is not None):
            # PLUS
            return plus
        self._reset(_begin_pos)
        if ((repetition := self._Repetition()) is not None):
            # Repetition
            return repetition
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MetaDefBody__GEN_1(self):
        _begin_pos = self._mark()
        if ((esccurclose := self._EscCurClose()) is not None):
            # EscCurClose
            return esccurclose
        self._reset(_begin_pos)
        if ((_1 := self._expectc()) is not None):
            # .
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MetaDefBody__GEN_2(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._expectc, '}') is not None
            and (_1 := self._MetaDefBody__GEN_1()) is not None
        ):
            # !'}' MetaDefBody__GEN_1
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Literal__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._ranges, ("'", "'")) is not None
            and (char := self._Char()) is not None
        ):
            # !['] Char
            return char
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Literal__GEN_2(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._ranges, ('"', '"')) is not None
            and (char := self._Char()) is not None
        ):
            # !["] Char
            return char
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Class__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._expectc, ']') is not None
            and (range := self._Range()) is not None
        ):
            # !']' Range
            return range
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Repetition__GEN_1(self):
        _begin_pos = self._mark()
        if (
            (number := self._Number()) is not None
            and self._expectc(',') is not None
            and (number1 := self._Number()) is not None
        ):
            # Number ',' Number
            return [number, number1]
        self._reset(_begin_pos)
        if ((number := self._Number()) is not None):
            # Number
            return number
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Spacing__GEN_1(self):
        _begin_pos = self._mark()
        if ((space := self._Space()) is not None):
            # Space
            return space
        self._reset(_begin_pos)
        if ((comment := self._Comment()) is not None):
            # Comment
            return comment
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Comment__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._EndOfLine) is not None
            and (_1 := self._expectc()) is not None
        ):
            # !EndOfLine .
            return _1
        self._reset(_begin_pos)
        return None


if __name__ == '__main__':
    from argparse import ArgumentParser, FileType
    import sys

    argparser = ArgumentParser()
    argparser.add_argument('input_file', nargs='?',
                           type=FileType('r', encoding='UTF-8'),
                           default=sys.stdin)

    ns = argparser.parse_args()

    reader = Reader(ns.input_file)
    parser = Parser(reader)
    result = parser.parse()

    if result is not None:
        print(repr(result))

    exit(result is None)  # Unix-style: 0 is success
