# NOTE: __future__.annotations can cause problems with dataclasses_json
from __future__ import annotations

import string

from typing import Optional, Any, Iterator
from collections.abc import Iterable, Sized
from abc import abstractmethod
from itertools import chain

from polygen.attrholder import AttributeHolder, ArgsRepr
from .utility import isiterable, wrap_string


class Node(Iterable):
    def __init__(self, begin_pos: int = 0, end_pos: int = 0):
        self.begin_pos = begin_pos
        self.end_pos = end_pos

    @property
    def descendants(self) -> Iterator[Node]:
        yield self
        for e in self:
            yield from e.descendants

    @abstractmethod
    def __iter__(self) -> Iterator[Node]:
        ...

    def copy(self, deep=False) -> Node:
        nodes = []
        for node in self:
            if deep:
                node = node.copy(deep=True)
            nodes.append(node)

        self_type = type(self)
        return self_type(*nodes)

    def to_dict(self):
        type_name = type(self).__name__
        dct = {'type': type_name}
        for k, v in self._get_kwargs():
            if isinstance(v, Node):
                v = v.to_dict()
            elif isiterable(v):
                v = [(i.to_dict() if isinstance(i, Node) else i) for i in v]
            dct[k] = v
        return dct

    def __bool__(self):
        return True


class LeafNode(Node):
    @property
    def descendants(self) -> Iterator[LeafNode]:
        yield self

    def __iter__(self) -> Iterator[Node]:
        yield from tuple()

    def copy(self, deep=False) -> Node:
        return type(self)()


class Grammar(Node, ArgsRepr, Sized):
    nodes: list[Rule | MetaRule]
    entry: Optional[Rule]

    def __init__(self, *rules, begin_pos=0, end_pos=0):
        self.nodes = list(rules)
        self.entry = None
        super().__init__(begin_pos, end_pos)

    def add(self, rule: Rule) -> bool:
        if rule in self.nodes:
            return False
        self.nodes.append(rule)
        return True

    def remove_metarules(self):
        self.nodes = list(filter(lambda i: type(i) is not MetaRule, self.nodes))

    def _get_args(self):
        return self.nodes

    def __eq__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self.rules == other.rules

    def __iter__(self):
        yield from self.nodes

    def __len__(self):
        return len(self.nodes)

    def __str__(self):
        return '\n'.join(map(str, self.nodes))


class Expression(Node, ArgsRepr, Sized):
    alts: list[Alt]

    def __init__(self, *alts, begin_pos=0, end_pos=0):
        self.alts = list(alts)
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        return self.alts

    def __iter__(self):
        yield from self.alts

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return NotImplemented
        return self.alts == other.alts

    def __add__(self, other):
        if not isinstance(other, Expression):
            raise TypeError
        return Expression(*chain(iter(self.alts), iter(other.alts)))

    def __len__(self):
        return len(self.alts)

    def __str__(self):
        alts = ', '.join(map(str, self.alts))
        return f"Expression({alts})"


class Rule(Node, ArgsRepr, Sized):
    id: Identifier
    expr: Expression
    directives: list[str]
    leftrec: bool

    def __init__(self, id, expr, directives=[],
                 leftrec=False, begin_pos=0, end_pos=0):
        self.id = id
        self.expr = expr
        self.directives = directives
        self.leftrec = leftrec
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        return [self.id, self.expr]

    def __str__(self):
        directives = ('[' + ', '.join(self.directives) + ']'
                      if self.directives else '')
        return f'Rule{directives}({self.id}, {self.rhs})'

    def __iter__(self):
        yield from (self.id, self.expr)

    def __len__(self):
        return len(self.expr)

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return NotImplemented
        return (self.id, self.expr) == (other.id, other.expr)

    def __hash__(self):
        return hash(self.id)


class MetaRef(LeafNode, ArgsRepr):
    id: Identifier

    def __init__(self, id, begin_pos=0, end_pos=0):
        self.id = id
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        return [self.id]

    def _get_kwargs(self):
        return [('id', self.id)]

    def __eq__(self, other):
        if not isinstance(other, MetaRef):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class MetaRule(Node, ArgsRepr):
    expr: str
    id: Optional[Identifier]

    def __init__(self, expr, id=None, begin_pos=0, end_pos=0):
        self.expr = expr
        self.id = id
        super().__init__(begin_pos, end_pos)

    def copy(self, deep=False):
        return MetaRule(id=self.id, expr=self.expr)

    def _get_args(self):
        return [self.id, self.expr]

    def _get_kwargs(self):
        return [('id', self.id), ('expr', self.expr)]

    def __iter__(self):
        if self.id is not None:
            yield self.id
        else:
            yield from ()

    def __eq__(self, other):
        if not isinstance(other, MetaRule):
            return NotImplemented
        return (self.id, self.expr) == (other.id, other.expr)


class Identifier(LeafNode, ArgsRepr):
    string: str

    def __init__(self, string, begin_pos=0, end_pos=0):
        self.string = string
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        return [self.string]

    def __eq__(self, other):
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.string == other.string

    def __lt__(self, other):
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.string < other.string

    def copy(self, deep=False) -> Identifier:
        return Identifier(self.string)

    def __hash__(self):
        return hash(self.string)


class Alt(Node, ArgsRepr, Sized):
    parts: Node
    metarule: Optional[MetaRef | MetaRule]

    def __init__(self, *parts: Node, metarule=None, begin_pos=0, end_pos=0):
        self.metarule = metarule
        self.parts = list(parts)
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        return self.parts

    def _get_kwargs(self):
        return [('metarule', self.metarule), ('parts', self.parts)]

    def __eq__(self, other):
        if not isinstance(other, Alt):
            return NotImplemented
        return (self.metarule, self.parts) == (other.metarule, other.parts)

    def __iter__(self):
        yield from self.parts
        if self.metarule is not None:
            yield self.metarule

    def __len__(self):
        return len(self.parts)

    def __add__(self, other):
        if not isinstance(other, Alt):
            raise TypeError
        return Alt(*chain(iter(self.parts), iter(other.parts)))


class Part(Node, AttributeHolder):
    lookahead: Optional[And | Not]
    prime: Node
    quant: Optional[ZeroOrOne | ZeroOrMore | OneOrMore | Repetition]
    metaname: Optional[str]

    def __init__(self, prime, *, lookahead=None, quant=None,
                 metaname=None, begin_pos=0, end_pos=0):
        self.lookahead = lookahead
        self.prime = prime
        self.quant = quant
        self.metaname = metaname
        super().__init__(begin_pos, end_pos)

    def copy(self, deep=False):
        if deep:
            kwargs = {k: v.copy() for k, v in self._get_kwargs()}
        else:
            kwargs = dict(self._get_kwargs())
        return Part(**kwargs)

    def _get_kwargs(self):
        dct = {'metaname': self.metaname}
        if self.lookahead:
            dct['lookahead'] = self.lookahead
        dct['prime'] = self.prime
        if self.quant:
            dct['quant'] = self.quant
        return list(dct.items())

    def __eq__(self, other):
        if not isinstance(other, Part):
            return NotImplemented
        return ((self.lookahead, self.prime, self.quant, self.metaname) ==
                (other.lookahead, other.prime, other.quant, other.metaname))

    def __iter__(self):
        if self.lookahead:
            yield self.lookahead
        yield self.prime
        if self.quant:
            yield self.quant


class AnyChar(LeafNode, AttributeHolder):
    def __eq__(self, other):
        return True if isinstance(other, AnyChar) else NotImplemented


class String(Node, ArgsRepr):
    chars: list[Char]

    def __init__(self, *chars: Char, begin_pos=0, end_pos=0):
        self.contents = chars  # type: ignore[assignment]
        super().__init__(begin_pos, end_pos)

    @property
    def contents(self) -> list[Char]:
        return self.chars

    @contents.setter
    def contents(self, value: Iterable[Char] | Char) -> None:
        if isiterable(value):
            self.chars = list(value)
        elif type(value) is Char:
            self.chars = [value]
        else:
            raise TypeError(
                f"expected Iterable[Char] | Char, got {type(value)}")

    def _get_args(self):
        return self.chars

    def __eq__(self, other):
        if not isinstance(other, String):
            return NotImplemented
        return self.chars == other.chars

    def __len__(self):
        return len(self.chars)

    def __iter__(self) -> Iterator[Char]:
        yield from self.chars

    def __str__(self):
        string = ''.join(map(lambda c: str(c)[1:-1], self.chars))
        return wrap_string(string)


class Class(Node, ArgsRepr, Sized):
    ranges: list[Range]

    def __init__(self, *ranges: Range, begin_pos=0, end_pos=0):
        self.ranges = list(ranges)
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        return self.ranges

    def __eq__(self, other):
        if not isinstance(other, Class):
            return NotImplemented
        return self.ranges == other.ranges

    def __len__(self):
        return len(self.ranges)

    def __iter__(self):
        yield from self.ranges


class Range(Node, ArgsRepr):
    beg: Char
    end: Optional[Char]

    def __init__(self, beg, end=None, begin_pos=0, end_pos=0):
        self.beg = beg
        self.end = end
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        args = [self.beg, self.end] if self.end else [self.beg]
        return [str(a) for a in args]

    def _get_kwargs(self):
        return (('beg', self.beg), ('end', self.end))

    def __eq__(self, other):
        if not isinstance(other, Range):
            return NotImplemented
        return (self.beg, self.end) == (other.beg, other.end)

    def __iter__(self):
        yield self.beg
        if self.end:
            yield self.end


class Lookahead(LeafNode):
    def _get_kwargs(self):
        return ()

    def __eq__(self, other):
        return type(other) is type(self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        type_name = type(self).__name__
        return f"{type_name}()"

    def __str__(self):
        return type(self).__name__


class And(Lookahead):
    pass


class Not(Lookahead):
    pass


class Quantifier(LeafNode):
    def _get_kwargs(self):
        return ()

    def __eq__(self, other):
        return type(other) is type(self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        type_name = type(self).__name__
        return f"{type_name}()"

    def __str__(self):
        return type(self).__name__


class ZeroOrOne(Quantifier):
    pass


class ZeroOrMore(Quantifier):
    pass


class OneOrMore(Quantifier):
    pass


PredicateType = And | Not
QuantifierType = ZeroOrOne | ZeroOrMore | OneOrMore


class Repetition(LeafNode, ArgsRepr):
    beg: int
    end: Optional[int]

    def __init__(self, beg, end=None, begin_pos=0, end_pos=0):
        self.beg = beg
        self.end = end
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        if self.end:
            return [self.beg, self.end]
        else:
            return [self.beg]

    def __eq__(self, other):
        if not isinstance(other, Repetition):
            return NotImplemented
        return (self.beg, self.end) == (other.beg, other.end)


class Char(LeafNode, ArgsRepr):
    code: int

    def __init__(self, code: int | str, begin_pos=0, end_pos=0):
        self.code = ord(code) if isinstance(code, str) else code
        super().__init__(begin_pos, end_pos)

    def _get_args(self):
        assert isinstance(self.code, int), "char code is integer"
        if (c := chr(self.code)) and c in string.printable:
            return [c]
        return [self.code]

    def __eq__(self, other):
        if not isinstance(other, Char):
            return NotImplemented
        return self.code == other.code

    def __lt__(self, other):
        if not isinstance(other, Char):
            return NotImplemented
        return self.code < other.code

    def __gt__(self, other):
        if not isinstance(other, Char):
            return NotImplemented
        return self.code > other.code

    def __le__(self, other):
        return self.__eq__(other) or self.__lt(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __str__(self):
        if (c := chr(self.code)) and c in string.printable:
            return repr(c)
        return '\\u' + hex(self.code)[2:].rjust(4, '0')

    def __hash__(self):
        return hash(self.code)


class GrammarVisitor:
    # taken from pegen
    # https://github.com/we-like-parsers/pegen/blob/main/src/pegen/grammar.py

    def visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self,
                      node: Iterable[Any],
                      *args: Any,
                      **kwargs: Any) -> None:
        """Called if no explicit visitor function exists for a node."""
        for value in node:
            self.visit(value, *args, **kwargs)
