from __future__ import annotations
import string

from typing import Optional, Any
from collections.abc import Iterable, Sized
from enum import StrEnum
from itertools import chain

from .attrholder import AttributeHolder, ArgsRepr


class Node(Iterable):
    @property
    def descendants(self):
        def iterate():
            for child in self:
                if isinstance(child, Node):
                    yield from child.descendants
                else:
                    yield child

        yield from chain(self._yield(), *iterate())

    def __iter__(self):
        yield from tuple()

    def _yield(self):
        yield self


class Grammar(Node, AttributeHolder, Sized):
    def __init__(self, rules: Iterable[Rule]):
        self.rules = {rule.name: rule for rule in rules}

    def __iter__(self):
        yield from self.rules.values()

    def __len__(self):
        return len(self.rules)

    def __str__(self):
        return '\n'.join(map(str, self.rules.values()))


class Expression(Node, ArgsRepr, Sized):
    def __init__(self, alts: Iterable[Alt]):
        self.alts = alts

    def _get_args(self):
        return [self.alts]

    def __iter__(self):
        yield from self.alts

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return NotImplemented
        return self.alts == other.alts

    def __add__(self, other):
        if not isinstance(other, Expression):
            raise TypeError
        return Expression(list(self.alts) + list(other.alts))

    def __len__(self):
        return len(self.alts)

    def __str__(self):
        alts = ', '.join(map(str, self.alts))
        return f"Expression({alts})"


class Rule(Node, ArgsRepr, Sized):
    def __init__(self, name: Identifier, rhs: Expression):
        self.name = name
        self.rhs = rhs

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


class Identifier(Node, ArgsRepr):
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

    def _get_args(self):
        return [self.parts]

    def __eq__(self, other):
        if not isinstance(other, Alt):
            return NotImplemented
        return self.parts == other.parts

    def __iter__(self):
        yield from self.parts

    def __len__(self):
        return len(self.parts)

    def __add__(self, other):
        if not isinstance(other, Alt):
            raise TypeError
        return Alt(list(self.parts) + list(other.parts))


class Part(Node, AttributeHolder):
    def __init__(self, *,
                 prime,
                 pred: Optional[Predicate] = None,
                 quant: Optional[Quantifier | Repetition] = None):
        self.pred = pred
        self.prime = prime
        self.quant = quant

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
        if self.pred:
            yield self.pred
        yield self.prime
        if self.quant:
            yield self.quant


class AnyChar(Node, AttributeHolder):
    def __eq__(self, other):
        return True if isinstance(other, AnyChar) else NotImplemented


class Literal(Node, ArgsRepr):
    def __init__(self, chars):
        self.chars = chars

    def _get_args(self):
        return [self.chars]

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return NotImplemented
        return self.chars == other.chars

    def __len__(self):
        return len(self.chars)

    def __iter__(self):
        yield from self.chars

    def __str__(self):
        lit = ''.join(map(str, self.chars))
        return f"Literal({lit!r})"


class Class(Node, ArgsRepr, Sized):
    def __init__(self, ranges: Iterable[Range]):
        self.ranges = ranges

    def _get_args(self):
        return [self.ranges]

    def __eq__(self, other):
        if not isinstance(other, Class):
            return NotImplemented
        return self.ranges == other.ranges

    def __len__(self):
        return len(self.ranges)

    def __iter__(self):
        yield from self.ranges


class Range(Node, ArgsRepr):
    def __init__(self, beg: Char, end: Optional[Char] = None):
        self.beg = beg
        self.end = end

    def _get_args(self):
        args = [self.beg, self.end] if self.end else [self.beg]
        return [repr(str(a)) for a in args]

    def __eq__(self, other):
        if not isinstance(other, Range):
            return NotImplemented
        return (self.beg, self.end) == (other.beg, other.end)

    def __iter__(self):
        yield self.beg
        if self.end:
            yield self.end


def _enum_evaluable_repr(cls):
    """
    Changes default enum class' representation to evaluable

    The default repr of an enum member "FOO" with value 42 of an
    enum "MyEnum" is:

    ```python
    MyEnum.FOO: 42>
    ```

    `_enum_evaluable_repr` makes it:

    ```python
    MyEnum.FOO
    ```
    """

    def _repr(self):
        class_name = self.__class__.__name__
        self_name = self.name
        return f"{class_name}.{self_name}"

    cls.__repr__ = _repr
    return cls


@_enum_evaluable_repr
class Predicate(Node, StrEnum):
    NOT = '!'
    AND = '&'


@_enum_evaluable_repr
class Quantifier(Node, StrEnum):
    OPTIONAL = '?'
    ZERO_OR_MORE = '*'
    ONE_OR_MORE = '+'


class Repetition(Node, ArgsRepr):
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


class Char(Node, ArgsRepr):
    def __init__(self, code: int | str):
        if isinstance(code, str):
            self.code = ord(code)
        else:
            self.code = code

    def _get_args(self):
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
        return not self.__eq(other)

    def __le__(self, other):
        return self.__eq__(other) or self.__lt(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __str__(self):
        if (c := chr(self.code)) and c in string.printable:
            return c
        return '\\u' + hex(self.code)[2:].rjust(4, '0')


class GrammarVisitor:
    # stolen from pegen
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
            if isinstance(value, list):
                for item in value:
                    self.visit(item, *args, **kwargs)
            else:
                self.visit(value, *args, **kwargs)


def common_prefix(lhs: Node, rhs: Node) -> Optional[list[Node]]:
    parts = []
    for a, b in zip(lhs, rhs):
        if a != b:
            return None
        parts.append(a)
    return parts


def has_prefix(prefix: list[Node], node: Grammar | Expression) -> bool:
    if len(node) < len(prefix):
        return False
    for a, b in zip(prefix, node):
        if a != b:
            return False
    return True
