from __future__ import annotations
import string

from typing import Optional, Any, Iterator
from collections.abc import Iterable, Sized
from abc import abstractmethod
from enum import StrEnum
from .fixes.enum_repr import enum_evaluable_repr
from itertools import zip_longest

from .attrholder import AttributeHolder, ArgsRepr


def seq_cmp(seq1, seq2):
    return all(i == j for i, j in zip_longest(seq1, seq2))


class Node(Iterable):
    def __init__(self, *args, **kwargs):
        self._parent = None

    @property
    def descendants(self) -> Iterator[Node]:
        yield self
        for e in self:
            yield from e.descendants

    @property
    def parent(self) -> Node:
        return self._parent

    def _set_parent(self, nodes: Iterable[Node]):
        for node in nodes:
            if node is not None:
                node._parent = self

    @abstractmethod
    def __iter__(self):
        ...


class LeafNode(Node):
    @property
    def descendants(self) -> Iterator[LeafNode]:
        yield self

    def __iter__(self):
        yield from tuple()


class Grammar(Node, AttributeHolder, Sized):
    def __init__(self, rules: Iterable[Rule]):
        self.nodes = list(rules)
        self.rules = {rule.name: rule for rule in rules}
        self._set_parent(self.nodes)

    def add(self, rule: Rule) -> bool:
        if rule.name in self.rules:
            return False
        self.nodes.append(rule)
        self.rules[rule.name] = rule
        return True

    def __iter__(self):
        yield from self.rules.values()

    def __len__(self):
        return len(self.rules)

    def __str__(self):
        return '\n'.join(map(str, self.rules.values()))

    def __bool__(self):
        return True


class Expression(Node, ArgsRepr, Sized):
    def __init__(self, alts: Iterable[Alt]):
        self.alts = alts
        self._set_parent(self.alts)

    def _get_args(self):
        return [self.alts]

    def __iter__(self):
        yield from self.alts

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return NotImplemented
        return seq_cmp(self.alts, other.alts)

    def __add__(self, other):
        if not isinstance(other, Expression):
            raise TypeError
        return Expression(list(self.alts) + list(other.alts))

    def __len__(self):
        return len(self.alts)

    def __str__(self):
        alts = ', '.join(map(str, self.alts))
        return f"Expression({alts})"

    def __bool__(self):
        return True


class Rule(Node, ArgsRepr, Sized):
    def __init__(self, name: Identifier, rhs: Expression):
        self.name = name
        self.rhs = rhs
        self._set_parent([self.name, self.rhs])

    def _get_args(self):
        return [self.name, self.rhs]

    def __iter__(self):
        yield self.rhs

    def __len__(self):
        return len(self.rhs)

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return NotImplemented
        return (self.name, self.rhs) == (other.name, other.rhs)

    def __bool__(self):
        return True


class Identifier(LeafNode, ArgsRepr):
    def __init__(self, string: str):
        self.string = string

    def _get_args(self):
        return [self.string]

    def __eq__(self, other):
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.string == other.string

    def __hash__(self):
        return hash(self.string)


class Alt(Node, ArgsRepr, Sized):
    def __init__(self, parts: Iterable[Part]):
        self.parts = parts
        self._set_parent(self.parts)

    def _get_args(self):
        return [self.parts]

    def __eq__(self, other):
        if not isinstance(other, Alt):
            return NotImplemented
        return seq_cmp(self.parts, other.parts)

    def __iter__(self):
        yield from self.parts

    def __len__(self):
        return len(self.parts)

    def __add__(self, other):
        if not isinstance(other, Alt):
            raise TypeError
        return Alt(list(self.parts) + list(other.parts))

    def __bool__(self):
        return True


class Part(Node, AttributeHolder):
    def __init__(self, *,
                 prime,
                 pred: Optional[Predicate] = None,
                 quant: Optional[Quantifier | Repetition] = None):
        self.pred = pred
        self.prime = prime
        self.quant = quant
        self._set_parent([self.pred, self.prime, self.quant])

    def _get_kwargs(self):
        dct = {}
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
        yield self.prime


class AnyChar(LeafNode, AttributeHolder):
    def __eq__(self, other):
        return True if isinstance(other, AnyChar) else NotImplemented


class Literal(Node, ArgsRepr):
    def __init__(self, chars):
        self.chars = chars
        self._set_parent(self.chars)

    def _get_args(self):
        return [self.chars]

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return NotImplemented
        return seq_cmp(self.chars, other.chars)

    def __len__(self):
        return len(self.chars)

    def __iter__(self):
        yield from self.chars

    def __str__(self):
        lit = ''.join(map(str, self.chars))
        return f"Literal({lit!r})"

    def __bool__(self):
        return True


class Class(Node, ArgsRepr, Sized):
    def __init__(self, ranges: Iterable[Range]):
        self.ranges = ranges
        self._set_parent(self.ranges)

    def _get_args(self):
        return [self.ranges]

    def __eq__(self, other):
        if not isinstance(other, Class):
            return NotImplemented
        return seq_cmp(self.ranges, other.ranges)

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
        self._set_parent([beg, end])

    def _get_args(self):
        args = [self.beg, self.end] if self.end else [self.beg]
        return [str(a) for a in args]

    def __eq__(self, other):
        if not isinstance(other, Range):
            return NotImplemented
        return (self.beg, self.end) == (other.beg, other.end)

    def __iter__(self):
        yield self.beg
        if self.end:
            yield self.end


class _EnumNodeMeta(type(StrEnum), type(LeafNode)):  # type: ignore
    pass


@enum_evaluable_repr
class Predicate(LeafNode, StrEnum, metaclass=_EnumNodeMeta):
    # enum members are typed due to mypy bug:
    #     error: Argument "quant" to "Part" has incompatible type "str";
    #     expected "Quantifier | Repetition | None"  [arg-type]
    NOT: Predicate = '!'  # type: ignore
    AND: Predicate = '&'  # type: ignore


@enum_evaluable_repr
class Quantifier(LeafNode, StrEnum, metaclass=_EnumNodeMeta):
    OPTIONAL: Quantifier = '?'  # type: ignore
    ZERO_OR_MORE: Quantifier = '*'  # type: ignore
    ONE_OR_MORE: Quantifier = '+'  # type: ignore


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
            return c
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
