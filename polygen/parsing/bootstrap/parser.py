# This is automatically generated code, do not edit.
# Generated by Polygen 0.1.0
# 2024-05-12 10:18 AM


from __future__ import annotations

from typing import Optional
from functools import wraps

from polygen.parsing.reader import Reader
from polygen.grammar.node import (
    Node,
    Grammar,
    Expression,
    Rule,
    MetaRef,
    MetaRule,
    Identifier,
    Range,
    Alt,
    Part,
    AnyChar,
    String,
    Class,
    Not,
    And,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    Char
)


def isnode(obj):
    return isinstance(obj, Node)


def memoize(fn):

    @wraps(fn)
    def wrapper(self, *args):
        pos = self._mark()
        key = (fn, args, pos)
        memo = self._memos.get(key)
        if memo is None:
            result = fn(self, *args)
            endpos = self._mark()
            self._memos[key] = result, endpos
        else:
            result, endpos = memo
            self._reset(endpos)
        return result

    return wrapper


def memoize_lr(fn):

    @wraps(fn)
    def wrapper(self, *args):
        pos = self._mark()
        key = (fn, args, pos)
        memo = self._memos.get(key)

        # if not growing a seed parse, return memo
        lr = self._leftrec
        if lr is not None:

            # do not evaluate rule that is not involved in the leftrec
            if fn not in {lr.head} | lr.involved_set:
                memo = None, pos

            # involved rules are evaluated only once
            # during a seed-growing iteration
            elif fn in lr.eval_set:
                lr.eval_set.remove(fn)
                result = fn(self, *args)
                endpos = self._mark()
                memo = result, endpos

        if memo is None:
            # prime a cache with a failure
            self._memos[key] = lastres, lastpos = None, pos

            # loop until no longer parse is obtained
            while True:
                self._reset(pos)
                result = fn(self, *args)
                endpos = self._mark()
                if endpos <= lastpos:
                    break
                self._memos[key] = lastres, lastpos = result, endpos

            result = lastres
            self._reset(lastpos)

        else:
            result, endpos = memo
            self._reset(endpos)

        return result

    return wrapper


class LR:
    def __init__(self, head, involved_set):
        self.head = head.__wrapped__
        self.involved_set = set(fn.__wrapped__ for fn in involved_set)
        self.eval_set = set(fn.__wrapped__ for fn in involved_set)

    def __repr__(self):
        return f"LR(head={self.head}, involved_set={self.involved_set})"

    def __str__(self):
        return self.__repr__()


class Parser:
    def __init__(self, stream, actions=None):
        self._memos = {}
        self._leftrec = None
        self.reader = Reader(stream)
        self.chars: list[str] = []
        self.actions = actions
        self.pos = 0

    @memoize
    def _expectc(self, char: str | None = None) -> Optional[str]:
        if c := self._peek_char():
            if char is not None and c != char:
                return None
            self.pos += 1
            return c
        return None

    @memoize
    def _expects(self, string: str) -> Optional[str]:
        pos = self._mark()
        for c in string:
            if c != self._peek_char():
                self._reset(pos)
                return None
            self.pos += 1
        return string

    def _lookahead(self, positive, fn, *args):
        pos = self._mark()
        ok = fn(*args) is not None
        self._reset(pos)
        return ok == positive

    def _loop(self, nonempty, fn, *args):
        pos = self._mark()
        nodes = []
        while (node := fn(*args)) is not None:
            nodes.append(node)
        if len(nodes) >= nonempty:
            return nodes
        self._reset(pos)
        return None

    def _maybe(self, fn, *args):
        if (result := fn(*args)) is not None:
            return result
        return True

    def _get_char(self) -> str:
        char = self._peek_char()
        self.pos += 1
        return char

    def _peek_char(self) -> str:
        if self.pos == len(self.chars):
            self.chars.append(next(self.reader, None))
        return self.chars[self.pos]

    def _mark(self) -> int:
        return self.pos

    def _reset(self, pos: int):
        self.pos = pos

    def _action(self, rulename, *args, **kwargs):
        if self.actions is not None:
            fn = getattr(self.actions, rulename, None)
            if fn:
                return fn(**kwargs)
        return args

    def parse(self):
        return self._Grammar()

    @memoize
    def _Grammar(self):
        _begin_pos = self._mark()
        if (
            self._Spacing() is not None
            and (entity := self._loop(True, self._Entity)) is not None
            and (endoffile := self._EndOfFile()) is not None
        ):
            # grammar_action
            return Grammar(*entity, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Entity(self):
        _begin_pos = self._mark()
        if ((definition := self._Definition()) is not None):
            return definition
        self._reset(_begin_pos)
        if ((metadef := self._MetaDef()) is not None):
            return metadef
        self._reset(_begin_pos)
        return None

    @memoize
    def _Definition(self):
        _begin_pos = self._mark()
        if (
            (directive := self._loop(False, self._Directive)) is not None
            and (identifier := self._Identifier()) is not None
            and self._LEFTARROW() is not None
            and (expression := self._Expression()) is not None
        ):
            # def_action
            return Rule(identifier, expression, directives=directive,
                        begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if ((metadef := self._MetaDef()) is not None):
            return metadef
        self._reset(_begin_pos)
        return None

    @memoize
    def _Directive(self):
        _begin_pos = self._mark()
        if (
            self._AT() is not None
            and (dirname := self._DirName()) is not None
            and self._Spacing() is not None
        ):
            # directive_action
            return dirname.string
        self._reset(_begin_pos)
        return None

    @memoize
    def _DirName(self):
        _begin_pos = self._mark()
        if ((identifier := self._Identifier()) is not None):
            return identifier
        self._reset(_begin_pos)
        return None

    @memoize
    def _Expression(self):
        _begin_pos = self._mark()
        if (
            (sequence := self._Sequence()) is not None
            and (seqs := self._loop(False, self._Expression__GEN_1)) is not None
        ):
            # expr_action
            return Expression(sequence, *seqs, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Sequence(self):
        _begin_pos = self._mark()
        if (
            (parts := self._loop(False, self._Prefix)) is not None
            and (m := self._maybe(self._MetaRule)) is not None
        ):
            # sequence_action
            m = m if isnode(m) else None
            return Alt(*parts, metarule=m, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Prefix(self):
        _begin_pos = self._mark()
        if (
            (metaname := self._maybe(self._MetaName)) is not None
            and (lookahead := self._maybe(self._Prefix__GEN_1)) is not None
            and (suffix := self._Suffix()) is not None
        ):
            # prefix_action
            metaname = metaname if isinstance(metaname, str) else None
            lookahead = lookahead if isnode(lookahead) else None
            prime, quant = suffix
            quant = quant if isnode(quant) else None
            return Part(lookahead=lookahead, prime=prime, quant=quant, metaname=metaname,
                        begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Suffix(self):
        _begin_pos = self._mark()
        if (
            (primary := self._Primary()) is not None
            and (_1 := self._maybe(self._Suffix__GEN_1)) is not None
        ):
            return primary, _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Primary(self):
        _begin_pos = self._mark()
        if (
            (identifier := self._Identifier()) is not None
            and self._lookahead(False, self._LEFTARROW)
        ):
            return identifier
        self._reset(_begin_pos)
        if (
            self._OPEN() is not None
            and (expression := self._Expression()) is not None
            and self._CLOSE() is not None
        ):
            return expression
        self._reset(_begin_pos)
        if ((literal := self._Literal()) is not None):
            return literal
        self._reset(_begin_pos)
        if ((_class := self._Class()) is not None):
            return _class
        self._reset(_begin_pos)
        if ((dot := self._DOT()) is not None):
            return dot
        self._reset(_begin_pos)
        return None

    @memoize
    def _MetaName(self):
        _begin_pos = self._mark()
        if (
            (identifier := self._Identifier()) is not None
            and self._SEMI() is not None
        ):
            # metaname_action
            return identifier.string
        self._reset(_begin_pos)
        return None

    @memoize
    def _MetaRule(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expects("${")) is not None
            and (expr := self._loop(False, self._MetaRule__GEN_1)) is not None
            and (_2 := self._expectc('}')) is not None
            and self._Spacing() is not None
        ):
            # metarule_def_action
            string = ''.join(expr)
            return MetaRule(expr=string, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if (
            (_1 := self._expectc('$')) is not None
            and self._Spacing() is not None
            and (identifier := self._Identifier()) is not None
            and self._lookahead(False, self._expectc, '{')
        ):
            # metarule_ref_action
            return MetaRef(identifier, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _MetaDef(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('$')) is not None
            and self._Spacing() is not None
            and (identifier := self._Identifier()) is not None
            and (expr := self._MetaDefBody()) is not None
        ):
            # metadef_action
            return MetaRule(id=identifier, expr=expr,
                            begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _MetaDefBody(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('{')) is not None
            and (expr := self._loop(False, self._MetaRule__GEN_1)) is not None
            and (_2 := self._expectc('}')) is not None
            and self._Spacing() is not None
        ):
            # metadef_body_action
            return ''.join(expr)
        self._reset(_begin_pos)
        return None

    @memoize
    def _NestedBody(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('{')) is not None
            and (body := self._loop(False, self._MetaRule__GEN_1)) is not None
            and (_2 := self._expectc('}')) is not None
        ):
            # nested_body_action
            string = ''.join(body)
            return f"{{{string}}}"
        self._reset(_begin_pos)
        return None

    @memoize
    def _Identifier(self):
        _begin_pos = self._mark()
        if (
            (start := self._IdentStart()) is not None
            and (cont := self._loop(False, self._IdentCont)) is not None
            and self._Spacing() is not None
        ):
            # ident_action
            string = ''.join((start, *cont))
            return Identifier(string, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _IdentStart(self):
        _begin_pos = self._mark()
        if ((_1 := self._IdentStart__GEN_1()) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _IdentCont(self):
        _begin_pos = self._mark()
        if ((identstart := self._IdentStart()) is not None):
            return identstart
        self._reset(_begin_pos)
        if ((_1 := self._IdentCont__GEN_1()) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Literal(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._Literal__GEN_1()) is not None
            and (chars := self._loop(False, self._Literal__GEN_2)) is not None
            and (_2 := self._Literal__GEN_1()) is not None
            and self._Spacing() is not None
        ):
            # literal_action
            if len(chars) == 1:
              return chars[0]
            return String(*chars, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if (
            (_1 := self._Literal__GEN_3()) is not None
            and (chars := self._loop(False, self._Literal__GEN_4)) is not None
            and (_2 := self._Literal__GEN_3()) is not None
            and self._Spacing() is not None
        ):
            # literal_action
            if len(chars) == 1:
              return chars[0]
            return String(*chars, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Class(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('[')) is not None
            and (ranges := self._loop(False, self._Class__GEN_1)) is not None
            and (_2 := self._expectc(']')) is not None
            and self._Spacing() is not None
        ):
            # class_action
            return Class(*ranges, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Range(self):
        _begin_pos = self._mark()
        if (
            (beg := self._Char()) is not None
            and (_1 := self._expectc('-')) is not None
            and (end := self._Char()) is not None
        ):
            # range_2_action
            return Range(beg, end, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if ((beg := self._Char()) is not None):
            # range_1_action
            return Range(beg, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Char(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('\\')) is not None
            and (char := self._Char__GEN_1()) is not None
        ):
            # esc_char_action
            CHR_MAP = {
                'n': Char('\n'),
                'r': Char('\r'),
                't': Char('\t'),
                '\'': Char('\''),
                '\"': Char('\"'),
                '[': Char('['),
                ']': Char(']'),
                '\\': Char('\\')
            }
            node = CHR_MAP[char]
            node.begin_pos = _begin_pos
            node.end_pos = self._mark()
            return node
        self._reset(_begin_pos)
        if (
            (_1 := self._expectc('\\')) is not None
            and (char1 := self._Char__GEN_2()) is not None
            and (char2 := self._Char__GEN_3()) is not None
            and (char3 := self._Char__GEN_3()) is not None
        ):
            # oct_char_action_1
            string = ''.join((char1, char2, char3))
            return Char(int(string, base=8), begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if (
            (_1 := self._expectc('\\')) is not None
            and (char1 := self._Char__GEN_3()) is not None
            and (char2 := self._maybe(self._Char__GEN_3)) is not None
        ):
            # oct_char_action_2
            char2 = char2 if isinstance(char2, str) else ''
            string = ''.join((char1, char2))
            return Char(int(string, base=8), begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if (
            (_1 := self._expects("\\u")) is not None
            and (chars := self._Char__GEN_4()) is not None
        ):
            # unicode_char_action
            string = ''.join(chars)
            return Char(int(string, base=16), begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        if (
            self._lookahead(False, self._expectc, '\\')
            and (any := self._AnyChar__GEN()) is not None
        ):
            # any_char_action
            return Char(ord(any), begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Repetition(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('{')) is not None
            and (grp := self._Repetition__GEN_1()) is not None
            and (_2 := self._expectc('}')) is not None
            and self._Spacing() is not None
        ):
            # rep_action
            beg, end = grp if isinstance(grp, tuple) else (grp, None)
            return Repetition(beg, end, begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _Number(self):
        _begin_pos = self._mark()
        if ((chars := self._loop(True, self._IdentCont__GEN_1)) is not None):
            # number_action
            string = ''.join(chars)
            return int(string)
        self._reset(_begin_pos)
        return None

    @memoize
    def _HexDigit(self):
        _begin_pos = self._mark()
        if ((char := self._HexDigit__GEN_1()) is not None):
            return char
        self._reset(_begin_pos)
        return None

    @memoize
    def _LEFTARROW(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expects("<-")) is not None
            and self._Spacing() is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _SLASH(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('/')) is not None
            and self._Spacing() is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _AND(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('&')) is not None
            and self._Spacing() is not None
        ):
            # and_action
            return And(begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _NOT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('!')) is not None
            and self._Spacing() is not None
        ):
            # not_action
            return Not(begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _QUESTION(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('?')) is not None
            and self._Spacing() is not None
        ):
            # optional_action
            return ZeroOrOne(begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _STAR(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('*')) is not None
            and self._Spacing() is not None
        ):
            # zero_or_more_action
            return ZeroOrMore(begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _PLUS(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('+')) is not None
            and self._Spacing() is not None
        ):
            # one_or_more_action
            return OneOrMore(begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _OPEN(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('(')) is not None
            and self._Spacing() is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _CLOSE(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc(')')) is not None
            and self._Spacing() is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _DOT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('.')) is not None
            and self._Spacing() is not None
        ):
            # dot_action
            return AnyChar(begin_pos=_begin_pos, end_pos=self._mark())
        self._reset(_begin_pos)
        return None

    @memoize
    def _AT(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('@')) is not None
            and self._Spacing() is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _SEMI(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc(':')) is not None
            and self._Spacing() is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Spacing(self):
        _begin_pos = self._mark()
        if ((_1 := self._loop(False, self._Spacing__GEN_1)) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Comment(self):
        _begin_pos = self._mark()
        if (
            (_1 := self._expectc('#')) is not None
            and (_2 := self._loop(False, self._Comment__GEN_1)) is not None
            and (endofline := self._EndOfLine()) is not None
        ):
            return _1, _2, endofline
        self._reset(_begin_pos)
        return None

    @memoize
    def _Space(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc(' ')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\t')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((endofline := self._EndOfLine()) is not None):
            return endofline
        self._reset(_begin_pos)
        return None

    @memoize
    def _EndOfLine(self):
        _begin_pos = self._mark()
        if ((_1 := self._expects("\r\n")) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\n')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\r')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _EndOfFile(self):
        _begin_pos = self._mark()
        if (self._lookahead(False, self._AnyChar__GEN)):
            return True
        self._reset(_begin_pos)
        return None

    @memoize
    def _AnyChar__GEN(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc()) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Expression__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._SLASH() is not None
            and (sequence := self._Sequence()) is not None
        ):
            return sequence
        self._reset(_begin_pos)
        return None

    @memoize
    def _Prefix__GEN_1(self):
        _begin_pos = self._mark()
        if ((_and := self._AND()) is not None):
            return _and
        self._reset(_begin_pos)
        if ((_not := self._NOT()) is not None):
            return _not
        self._reset(_begin_pos)
        return None

    @memoize
    def _Suffix__GEN_1(self):
        _begin_pos = self._mark()
        if ((question := self._QUESTION()) is not None):
            return question
        self._reset(_begin_pos)
        if ((star := self._STAR()) is not None):
            return star
        self._reset(_begin_pos)
        if ((plus := self._PLUS()) is not None):
            return plus
        self._reset(_begin_pos)
        if ((repetition := self._Repetition()) is not None):
            return repetition
        self._reset(_begin_pos)
        return None

    @memoize
    def _MetaRule__GEN_1(self):
        _begin_pos = self._mark()
        if ((nestedbody := self._NestedBody()) is not None):
            return nestedbody
        self._reset(_begin_pos)
        if (
            self._lookahead(False, self._expectc, '}')
            and (_1 := self._AnyChar__GEN()) is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _IdentStart__GEN_1(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('A')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('B')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('C')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('D')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('E')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('F')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('G')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('H')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('I')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('J')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('K')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('L')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('M')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('N')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('O')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('P')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('Q')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('R')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('S')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('T')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('U')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('V')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('W')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('X')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('Y')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('Z')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('_')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('a')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('b')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('c')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('d')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('e')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('f')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('g')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('h')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('i')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('j')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('k')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('l')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('m')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('n')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('o')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('p')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('q')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('r')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('s')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('t')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('u')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('v')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('w')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('x')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('y')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('z')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _IdentCont__GEN_1(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('0')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('1')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('2')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('3')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('4')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('5')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('6')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('7')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('8')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('9')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Literal__GEN_1(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc("'")) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Literal__GEN_2(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._Literal__GEN_1)
            and (char := self._Char()) is not None
        ):
            return char
        self._reset(_begin_pos)
        return None

    @memoize
    def _Literal__GEN_3(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('"')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Literal__GEN_4(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._Literal__GEN_3)
            and (char := self._Char()) is not None
        ):
            return char
        self._reset(_begin_pos)
        return None

    @memoize
    def _Class__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._expectc, ']')
            and (range := self._Range()) is not None
        ):
            return range
        self._reset(_begin_pos)
        return None

    @memoize
    def _Char__GEN_1(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('"')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc("'")) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('[')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('\\')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc(']')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('n')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('r')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('t')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Char__GEN_2(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('0')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('1')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('2')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Char__GEN_3(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('0')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('1')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('2')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('3')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('4')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('5')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('6')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('7')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Char__GEN_4(self):
        _begin_pos = self._mark()
        if (
            (hexdigit := self._HexDigit()) is not None
            and (hexdigit1 := self._HexDigit()) is not None
            and (hexdigit2 := self._HexDigit()) is not None
            and (hexdigit3 := self._HexDigit()) is not None
        ):
            return hexdigit, hexdigit1, hexdigit2, hexdigit3
        self._reset(_begin_pos)
        return None

    @memoize
    def _Repetition__GEN_1(self):
        _begin_pos = self._mark()
        if (
            (number := self._Number()) is not None
            and self._expectc(',') is not None
            and (number1 := self._Number()) is not None
        ):
            return number, number1
        self._reset(_begin_pos)
        if ((number := self._Number()) is not None):
            return number
        self._reset(_begin_pos)
        return None

    @memoize
    def _HexDigit__GEN_1(self):
        _begin_pos = self._mark()
        if ((_1 := self._expectc('0')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('1')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('2')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('3')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('4')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('5')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('6')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('7')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('8')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('9')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('A')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('B')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('C')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('D')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('E')) is not None):
            return _1
        self._reset(_begin_pos)
        if ((_1 := self._expectc('F')) is not None):
            return _1
        self._reset(_begin_pos)
        return None

    @memoize
    def _Spacing__GEN_1(self):
        _begin_pos = self._mark()
        if ((space := self._Space()) is not None):
            return space
        self._reset(_begin_pos)
        if ((comment := self._Comment()) is not None):
            return comment
        self._reset(_begin_pos)
        return None

    @memoize
    def _Comment__GEN_1(self):
        _begin_pos = self._mark()
        if (
            self._lookahead(False, self._EndOfLine)
            and (_1 := self._AnyChar__GEN()) is not None
        ):
            return _1
        self._reset(_begin_pos)
        return None


if __name__ == '__main__':
    from argparse import ArgumentParser, FileType
    import sys

    argparser = ArgumentParser()
    argparser.add_argument('input_file', type=FileType('r', encoding='UTF-8'),
                           default=sys.stdin)

    ns = argparser.parse_args()

    parser = Parser(ns.input_file)
    result = parser.parse()

    for r in result:
        print(repr(r), end='\n\n')

    print("Parsing successful" if result else "Parsing failure")
    exit(not result)  # Unix-style: 0 is success
