# This is automatically generated code, do not edit.
# Generated by Polygen 0.1.0


from __future__ import annotations

import io
import traceback

from functools import wraps
from typing import Optional, Union, Any, Tuple, Dict, List, Callable



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

    def __init__(self, stream: Optional[str | io.TextIOBase], bufsize=4096):
        self.bufsize = bufsize

        if stream is not None:
            self.reset(stream)

    def reset(self, stream: str | io.TextIOBase):
        self.buffer = ""
        self.stream = None
        self.buflen = 0
        self.pointer = 0
        self.line = 1
        self.column = 0
        self.eof = False

        if isinstance(stream, str):
            self.name = "<string>"
            self.buffer = stream
            self.buflen = len(self.buffer)
        elif isinstance(stream, io.IOBase):
            self.name = getattr(stream, "name", "<stream>")
            self.stream = stream

            if not stream.readable():
                raise ValueError(f"stream must be readable: {self.name}")

    def __iter__(self) -> Reader:
        return self

    def __next__(self) -> Token:
        if self.pointer == self.buflen:
            if not self.update():
                raise StopIteration
        char = self.buffer[self.pointer]
        tok = Token(char, self.line, self.column, self.column + 1, self.name)
        if char in '\r\n':
            self.line += 1
            self.column = 0
        else:
            self.column += 1
        self.pointer += 1
        return tok

    def update(self, length: int = 1) -> int:
        if self.eof or not self.stream:
            self.eof = True
            return 0
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        read_length = 0
        while len(self.buffer) < length:
            data = self.stream.read(self.bufsize)
            read_length += len(data)
            if data:
                self.buffer += data
            else:
                self.eof = True
                break
        self.buflen = len(self.buffer)
        return read_length

    @property
    def filename(self) -> str:
        return self.name

    def diagnose(self) -> Token:
        if not self.buflen and not self.update():
            return Token('', 0, 0, 0, self.name)
        if self.pointer == self.buflen:
            if not self.update():
                char = self.buffer[-1]
        else:
            char = self.buffer[self.pointer]
        return Token(char, self.line, self.column, self.column + 1, self.name)


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
            result = fn(self, *args)
            self._memos[key] = memo = _MemoEntry(result, self._mark())
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

    def __init__(self, reader: Reader, state: object | None = None): 
        self._memos = {}

        self._reader = reader
        self._tokens: List[Token] = []
        self._pos = 0

        self.state = state

        self._grow_rules: Dict[str, Tuple[List[Callable], List[Callable]]] = {
            "_Addition": ([self._Addition_Alt_3], [self._Addition_Alt_1, self._Addition_Alt_2]),
            "_Product": ([self._Product_Alt_4], [self._Product_Alt_1, self._Product_Alt_2, self._Product_Alt_3]),

        }

    @property
    def reader(self) -> Reader:
        return self._reader

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
            if count == end:
                return tokens
        if count >= beg:
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

    def make_syntax_error(self) -> SyntaxError:
        tok = self.reader.diagnose()
        return SyntaxError(
            tok.filename,
            (tok.filename, tok.line, tok.start, tok, tok.line, len(tok))
        )

    def parse(self, stream: str | io.TextIOBase) -> Any:
        self._reader.reset(stream)
        self._tokens.clear()
        self._memos.clear()
        self._pos = 0

        result = self._Calculator()
        if result is None:
            raise self.make_syntax_error()

        return result

    @_memoize
    def _Calculator(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('.')) is not None
            and (command := self._Command()) is not None
        ):
            # '.' Command
            return [_1, command]
        self._reset(_begin_pos)
        if (
            (expression := self._Expression()) is not None
            and (eof := self._EOF()) is not None
        ):
            # Expression EOF

            # Metarule: calculator
            self.state.print_result(expression)
            return []
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Expression(self):
        _begin_pos = self._mark()
        if ((addition := self._Addition()) is not None):
            # Addition
            return addition
        self._reset(_begin_pos)
        if ((command := self._Command()) is not None):
            # Command
            return command
        self._reset(_begin_pos)
        return None

    @_memoize_lr
    def _Addition(self):
        # Left recursive:
        #   Addition -> Addition
        #   Addition -> Addition
        if (alt := self._Addition_Alt_1()) is not None:
            return alt
        if (alt := self._Addition_Alt_2()) is not None:
            return alt
        if (alt := self._Addition_Alt_3()) is not None:
            return alt
        return None

    def _Addition_Alt_1(self):
        _begin_pos = self._mark()
        if (
            (addition := self._Addition()) is not None
            and (plus := self._PLUS()) is not None
            and (product := self._Product()) is not None
        ):
            # Addition PLUS Product

            # Metarule: addition
            return addition + product
        self._reset(_begin_pos)

    def _Addition_Alt_2(self):
        _begin_pos = self._mark()
        if (
            (addition := self._Addition()) is not None
            and (minus := self._MINUS()) is not None
            and (product := self._Product()) is not None
        ):
            # Addition MINUS Product

            # Metarule: substraction
            return addition - product
        self._reset(_begin_pos)

    def _Addition_Alt_3(self):
        _begin_pos = self._mark()
        if (
            (sign := self._maybe(self._Addition__GEN_1)) is not None
            and (product := self._Product()) is not None
        ):
            # Addition__GEN_1? Product

            # Metarule: product
            if sign and sign[0] == '-':
                return -product
            return product
        self._reset(_begin_pos)

    @_memoize_lr
    def _Product(self):
        # Left recursive:
        #   Product -> Product
        #   Product -> Product
        if (alt := self._Product_Alt_1()) is not None:
            return alt
        if (alt := self._Product_Alt_2()) is not None:
            return alt
        if (alt := self._Product_Alt_3()) is not None:
            return alt
        if (alt := self._Product_Alt_4()) is not None:
            return alt
        return None

    def _Product_Alt_1(self):
        _begin_pos = self._mark()
        if (
            (product := self._Product()) is not None
            and (pow := self._POW()) is not None
            and (term := self._Term()) is not None
        ):
            # Product POW Term

            # Metarule: power
            return product ** term
        self._reset(_begin_pos)

    def _Product_Alt_2(self):
        _begin_pos = self._mark()
        if (
            (product := self._Product()) is not None
            and (mul := self._MUL()) is not None
            and (term := self._Term()) is not None
        ):
            # Product MUL Term

            # Metarule: multiply
            return product * term
        self._reset(_begin_pos)

    def _Product_Alt_3(self):
        _begin_pos = self._mark()
        if (
            (product := self._Product()) is not None
            and (div := self._DIV()) is not None
            and (term := self._Term()) is not None
        ):
            # Product DIV Term

            # Metarule: divide
            return product / term
        self._reset(_begin_pos)

    def _Product_Alt_4(self):
        _begin_pos = self._mark()
        if ((term := self._Term()) is not None):
            # Term
            return term
        self._reset(_begin_pos)

    @_memoize
    def _Term(self):
        _begin_pos = self._mark()
        if ((number := self._Number()) is not None):
            # Number
            return number
        self._reset(_begin_pos)
        if ((function := self._Function()) is not None):
            # Function
            return function
        self._reset(_begin_pos)
        if ((variable := self._Variable()) is not None):
            # Variable
            return variable
        self._reset(_begin_pos)
        if (
            self._OPEN() is not None
            and (expression := self._Expression()) is not None
            and self._CLOSE() is not None
        ):
            # OPEN Expression CLOSE
            return expression
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Number(self):
        _begin_pos = self._mark()
        if ((decimal := self._Decimal()) is not None):
            # Decimal
            return decimal
        self._reset(_begin_pos)
        if ((integer := self._Integer()) is not None):
            # Integer
            return integer
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Integer(self):
        _begin_pos = self._mark()
        if (
            (i := self._loop(True, self._ranges, ('0', '9'))) is not None
            and self._Spacing() is not None
        ):
            # [0-9]+ Spacing

            # Metarule: integer
            return int(''.join(i))
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Decimal(self):
        _begin_pos = self._mark()
        if (
            (i := self._loop(True, self._ranges, ('0', '9'))) is not None
            and (dot := self._expectc('.')) is not None
            and (f := self._loop(True, self._ranges, ('0', '9'))) is not None
            and self._Spacing() is not None
        ):
            # [0-9]+ '.' [0-9]+ Spacing

            # Metarule: decimal_1
            parts = (*i, dot, *f)
            return float(''.join(parts))
        self._reset(_begin_pos)
        if (
            (i := self._loop(True, self._ranges, ('0', '9'))) is not None
            and (dot := self._expectc('.')) is not None
            and self._Spacing() is not None
        ):
            # [0-9]+ '.' Spacing

            # Metarule: decimal_2
            parts = (*i, dot, '0')
            return float(''.join(parts))
        self._reset(_begin_pos)
        if (
            (dot := self._expectc('.')) is not None
            and (f := self._loop(True, self._ranges, ('0', '9'))) is not None
            and self._Spacing() is not None
        ):
            # '.' [0-9]+ Spacing

            # Metarule: decimal_3
            parts = ('0', dot, *f)
            return float(''.join(parts))
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Function(self):
        _begin_pos = self._mark()
        if (
            (name := self._Identifier()) is not None
            and self._OPEN() is not None
            and (fnbody := self._maybe(self._FnBody)) is not None
            and self._CLOSE() is not None
        ):
            # Identifier OPEN FnBody? CLOSE

            # Metarule: function
            return self.state.function(name, *fnbody)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _FnBody(self):
        _begin_pos = self._mark()
        if (
            (expr := self._Expression()) is not None
            and (next := self._loop(False, self._FnBody__GEN_1)) is not None
        ):
            # Expression FnBody__GEN_1*

            # Metarule: function_body
            return expr, *next
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Variable(self):
        _begin_pos = self._mark()
        if ((name := self._Identifier()) is not None):
            # Identifier

            # Metarule: variable
            return self.state.variable(name)
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Identifier(self):
        _begin_pos = self._mark()
        if (
            (start := self._ranges(('a', 'z'), ('A', 'Z'))) is not None
            and (cont := self._loop(False, self._ranges, ('a', 'z'), ('A', 'Z'), ('_', '_'))) is not None
        ):
            # [a-zA-Z] [a-zA-Z_]*

            # Metarule: identifier
            return ''.join((start, *cont))
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Command(self):
        _begin_pos = self._mark()
        if ((quit := self._QUIT()) is not None):
            # QUIT

            # Metarule: quit
            self.state.quit = True
            return []
        self._reset(_begin_pos)
        if ((help := self._HELP()) is not None):
            # HELP

            # Metarule: help
            self.state.help()
            return []
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
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MINUS(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('-')) is not None
            and self._Spacing() is not None
        ):
            # '-' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _POW(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expects("**")) is not None
            and self._Spacing() is not None
        ):
            # "**" Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _MUL(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('*')) is not None
            and self._Spacing() is not None
        ):
            # '*' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _DIV(self):
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
    def _COMMA(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc(',')) is not None
            and self._Spacing() is not None
        ):
            # ',' Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _QUIT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expects("quit")) is not None
            and self._Spacing() is not None
        ):
            # "quit" Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _HELP(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expects("help")) is not None
            and self._Spacing() is not None
        ):
            # "help" Spacing
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Spacing(self):
        # Nullable
        _begin_pos = self._mark()
        if ((space := self._loop(False, self._Space)) is not None):
            # Nullable
            # Space*
            return space
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Space(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc(' ')) is not None):
            # ' '
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
        if ((_1 := self._expectc('\t')) is not None):
            # '\t'
            return _1
        self._reset(_begin_pos)
        return None

    @_memoize
    def _EOF(self):
        # Nullable
        _begin_pos = self._mark()
        if (self._lookahead(False, self._expectc) is not None):
            # Nullable
            # !.
            return []
        self._reset(_begin_pos)
        return None

    @_memoize
    def _Addition__GEN_1(self):
        _begin_pos = self._mark()
        if ((plus := self._PLUS()) is not None):
            # PLUS
            return plus
        self._reset(_begin_pos)
        if ((minus := self._MINUS()) is not None):
            # MINUS
            return minus
        self._reset(_begin_pos)
        return None

    @_memoize
    def _FnBody__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._COMMA() is not None
            and (expression := self._Expression()) is not None
        ):
            # COMMA Expression
            return expression
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

    reader = Reader(None)
    parser = Parser(reader)
    try:
        result = parser.parse(ns.input_file)
        print(repr(result))
    except SyntaxError as e:
        traceback.print_exception(SyntaxError, e, None)
        exit(1)

    exit(0)