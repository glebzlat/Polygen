from __future__ import annotations
import string
import re

from typing import Optional, Any, Iterator
from collections.abc import Iterable, Sized
from abc import abstractmethod
from itertools import zip_longest, chain

from .attrholder import AttributeHolder, ArgsRepr


def seq_cmp(seq1, seq2):
    return all(i == j for i, j in zip_longest(seq1, seq2))


class Node(Iterable):
    def __init__(self, begin_pos: int = 0, end_pos: int = 0):
        self._parent = None
        self._begin_pos, self._end_pos = begin_pos, end_pos

    @property
    def descendants(self) -> Iterator[Node]:
        yield self
        for e in self:
            yield from e.descendants

    @property
    def parent(self) -> Optional[Node]:
        return self._parent

    def _set_parent(self, nodes: Iterable[Optional[Node]]) -> None:
        for node in nodes:
            if node is not None:
                node._parent = self

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

    def dump(self) -> dict:
        """Create a dictinary from the Node.

        Created dictionary has `_node_type` item, which is a name
        of the corresponding node. It can be used to create nodes
        from the dictionary.
        """
        name = type(self).__name__
        dct = {'_node_type': name}
        for k, v in self._get_kwargs():
            if isinstance(v, Node):
                v = v.dump()
            elif isiterable(v):
                v = [(i.dump() if isinstance(i, Node) else i) for i in v]
            dct[k] = v
        return dct


class LeafNode(Node):
    @property
    def descendants(self) -> Iterator[LeafNode]:
        yield self

    def __iter__(self) -> Iterator[Node]:
        yield from tuple()

    def copy(self, deep=False) -> Node:
        return type(self)()


class Grammar(Node, ArgsRepr, Sized):
    def __init__(self, *rules: Rule | MetaRule):
        self._nodes = []

        self.rules = {}
        self.metarules = {}
        for r in rules:
            if isinstance(r, Rule):
                # This is a dirty hack to not to break the tree modification
                # rules: do not add MetaRules to the node list
                self._nodes.append(r)
                self.rules[r.id] = r
            elif isinstance(r, MetaRule):
                self.metarules[r.id] = r
            else:
                raise TypeError(f"incorrect rule type {type(r)}")

        self._entry: Optional[Rule] = None
        self._set_parent(self._nodes)
        self._set_parent(self.metarules.values())

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, value):
        self._nodes = value

    def add(self, rule: Rule) -> bool:
        if rule.id in self.rules:
            return False
        self.nodes.append(rule)
        self.rules[rule.name] = rule
        rule._parent = self
        return True

    @property
    def entry(self):
        return self._entry

    @entry.setter
    def entry(self, value):
        self._entry = value

    def _get_args(self):
        return self._nodes

    def _get_kwargs(self):
        return [('rules', self.rules.values()),
                ('metarules', self.metarules.values())]

    def __eq__(self, other):
        if not isinstance(other, Grammar):
            return NotImplemented
        return self.rules == other.rules

    def __iter__(self):
        yield from self.rules.values()
        yield from self.metarules.values()

    def __len__(self):
        return len(self.rules)

    def __str__(self):
        return '\n'.join(map(str, self.rules.values()))

    def __bool__(self):
        return True


class Expression(Node, ArgsRepr, Sized):
    def __init__(self, *alts: Alt):
        self.alts = list(alts)
        self._set_parent(self.alts)

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

    def __bool__(self):
        return True


class Rule(Node, ArgsRepr, Sized):
    def __init__(self,
                 name: Identifier,
                 rhs: Expression,
                 directives: list[str] | None = None):
        self.leftrec = False
        self.name = name
        self.rhs = rhs
        self._set_parent([self.name, self.rhs])
        self.directives = directives or []

    @property
    def id(self) -> Identifier:
        return self.name

    @id.setter
    def id(self, value) -> None:
        self.name = value
        self.name._parent = self

    @property
    def expression(self) -> Expression:
        return self.rhs

    @expression.setter
    def expression(self, value) -> None:
        self.rhs = value
        value._parent = self

    def _get_args(self):
        return [self.name, self.rhs]

    def __str__(self):
        directives_parts = (id.string for id in self.directives)
        directives = ('[' + ', '.join(directives_parts) + ']'
                      if self.directives else '')
        return f'Rule{directives}({self.name}, {self.rhs})'

    def __iter__(self):
        yield from (self.name, self.rhs)

    def __len__(self):
        return len(self.rhs)

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return NotImplemented
        return (self.name, self.rhs) == (other.name, other.rhs)

    def __bool__(self):
        return True


class MetaRef(LeafNode, ArgsRepr):
    def __init__(self, id: Identifier):
        self.id = id

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        self._id._parent = self

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
    def __init__(self, expr: str, id: Optional[Identifier] = None):
        self.id = id
        self.expr = expr

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        if self._id is not None:
            self._id._parent = self

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
    def __init__(self, string: str):
        self.string = string

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
    def __init__(self,
                 *parts: Node,
                 metarule: Optional[MetaRef | MetaRule] = None):
        self.metarule = metarule
        self.parts = list(parts)
        self._set_parent(self.parts)

    @property
    def metarule(self):
        return self._metarule

    @metarule.setter
    def metarule(self, value):
        self._metarule = value
        if self._metarule is not None:
            self._metarule._parent = self

    def _get_args(self):
        return self.parts

    def _get_kwargs(self):
        return [('metarule', self._metarule), ('parts', self.parts)]

    def __eq__(self, other):
        if not isinstance(other, Alt):
            return NotImplemented
        return self.parts == other.parts

    def __iter__(self):
        yield from self.parts
        if self._metarule is not None:
            yield self._metarule

    def __len__(self):
        return len(self.parts)

    def __add__(self, other):
        if not isinstance(other, Alt):
            raise TypeError
        return Alt(*chain(iter(self.parts), iter(other.parts)))

    def __bool__(self):
        return True


class Part(Node, AttributeHolder):
    def __init__(self, *,
                 prime,
                 pred: Optional[And | Not] = None,
                 quant: Optional[QuantifierType | Repetition] = None,
                 metaname: Optional[str] = None):
        self.pred = pred
        self.prime = prime
        self.quant = quant
        self.metaname = metaname

    @property
    def pred(self) -> Optional[PredicateType]:
        return self._pred

    @pred.setter
    def pred(self, value) -> None:
        self._pred = value
        if self._pred is not None:
            self._pred._parent = self

    @property
    def prime(self):
        return self._prime

    @prime.setter
    def prime(self, value) -> None:
        self._prime = value
        if self._prime is not None:
            self._prime._parent = self

    @property
    def quant(self) -> Optional[QuantifierType | Repetition]:
        return self._quant

    @quant.setter
    def quant(self, value) -> None:
        self._quant = value
        if self._quant is not None:
            self._quant._parent = self

    def copy(self, deep=False):
        if deep:
            kwargs = {k: v.copy() for k, v in self._get_kwargs()}
        else:
            kwargs = dict(self._get_kwargs())
        return Part(**kwargs)

    def _get_kwargs(self):
        dct = {'metaname': self.metaname}
        if self.pred:
            dct['pred'] = self.pred
        dct['prime'] = self.prime
        if self.quant:
            dct['quant'] = self.quant
        return list(dct.items())

    def __eq__(self, other):
        if not isinstance(other, Part):
            return NotImplemented
        return ((self.pred, self.prime, self.quant) ==
                (other.pred, other.prime, other.quant))

    def __iter__(self):
        if self.pred:
            yield self.pred
        yield self.prime
        if self.quant:
            yield self.quant


class AnyChar(LeafNode, AttributeHolder):
    def __eq__(self, other):
        return True if isinstance(other, AnyChar) else NotImplemented


def isiterable(obj: Any) -> bool:
    """Check if an object is iterable, but not string."""
    if isinstance(obj, str):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False


class String(Node, ArgsRepr):
    def __init__(self, *chars: Char):
        self.chars: list[Char]
        self.contents = chars  # type: ignore[assignment]

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
        for c in self.chars:
            c._parent = self

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

    _UNESCAPED_DOUBLE_QUOTE_RE = re.compile(r'(?<!\\)"')

    def __str__(self):
        string = ''.join(map(lambda c: str(c)[1:-1], self.chars))
        if self._UNESCAPED_DOUBLE_QUOTE_RE.match(string):
            string = string.replace('"', '\\"')
        return '"' + string + '"'

    def __bool__(self):
        return True


class Class(Node, ArgsRepr, Sized):
    def __init__(self, *ranges: Range):
        self.ranges = list(ranges)
        self._set_parent(self.ranges)

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

    def __bool__(self):
        return True


class Range(Node, ArgsRepr):
    def __init__(self, beg: Char, end: Optional[Char] = None):
        self.beg = beg
        self.end = end

    @property
    def beg(self) -> Char:
        return self._beg

    @beg.setter
    def beg(self, value) -> None:
        self._beg = value
        self._beg._parent = self

    @property
    def end(self) -> Optional[Char]:
        return self._end

    @end.setter
    def end(self, value) -> None:
        self._end = value
        if self._end is not None:
            self._end._parent = self

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


class Predicate(LeafNode):
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


class And(Predicate):
    pass


class Not(Predicate):
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
    def __init__(self, beg: int, end: Optional[int] = None):
        self.beg = beg
        self.end = end

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
    def __init__(self, code: int | str):
        if isinstance(code, str):
            self.code = ord(code)
        else:
            self.code = code

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

    def __ne__(self, other):
        return not self.__eq__(other)

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


def common_prefix(lhs: Node, rhs: Node) -> list[Node]:
    parts = []
    for a, b in zip(lhs, rhs):
        if a != b:
            break
        parts.append(a)
    return parts


def has_prefix(prefix: list[Node], node: Grammar | Expression) -> bool:
    if len(node) < len(prefix):
        return False
    for a, b in zip(prefix, node):
        if a != b:
            return False
    return True
