from __future__ import annotations
import string

from .attrholder import ArgsRepr


class Rule(ArgsRepr):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def _get_args(self):
        return [self.lhs, self.rhs]

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return NotImplemented
        return (self.lhs, self.rhs) == (other.lhs, other.rhs)


class Expression(ArgsRepr):
    def __init__(self, *sequences):
        self.sequences = sequences

    def _get_args(self):
        return list(self.sequences)

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return NotImplemented
        return self.sequences == other.sequences


class Sequence(ArgsRepr):
    def __init__(self, *parts):
        self.parts = parts

    def _get_args(self):
        return list(self.parts)

    def __eq__(self, other):
        if not isinstance(other, Sequence):
            return NotImplemented
        return self.parts == other.parts


class Identifier(ArgsRepr):
    def __init__(self, string):
        self.string = string

    def _get_args(self):
        return [self.string]

    def __eq__(self, other):
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.string == other.string


class Literal(ArgsRepr):
    def __init__(self, *chars):
        self.chars = chars

    def _get_args(self):
        return list(self.chars)

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return NotImplemented
        return self.chars == other.chars


class Class(ArgsRepr):
    def __init__(self, *ranges):
        self.ranges = ranges

    def _get_args(self):
        return list(self.ranges)

    def __eq__(self, other):
        if not isinstance(other, Class):
            return NotImplemented
        return self.ranges == other.ranges


class Range(ArgsRepr):
    def __init__(self, beg, end=None):
        self.beg = beg
        self.end = end

    def _get_args(self):
        if self.end:
            return [self.beg, self.end]
        else:
            return [self.beg]

    def __eq__(self, other):
        if not isinstance(other, Range):
            return NotImplemented
        return (self.beg, self.end) == (other.beg, other.end)


class NamedMembers:
    def get_member_name(self) -> str | None:
        class MemberWrapper:
            def __init__(self, string):
                self.string = string

            def __repr__(self):
                return self.string

            def __str__(self):
                return self.string

        dct = self.__class__.__dict__
        for attr, value in dct.items():
            if (attr.isupper() and isinstance(value, int) and
                    self.value == value):
                return MemberWrapper(f"{self.__class__.__name__}.{attr}")


class Predicate(ArgsRepr, NamedMembers):
    NOT = 1
    AND = 2

    def __init__(self, value: int):
        self.value = value

    def _get_args(self):
        return [self.get_member_name()]

    def __eq__(self, other):
        if not isinstance(other, Predicate):
            return NotImplemented
        return self.value == other.value


class Quantifier(ArgsRepr, NamedMembers):
    OPTIONAL = 1
    ZERO_OR_MORE = 2
    ONE_OR_MORE = 3

    def __init__(self, value: int | Repetition):
        self.value = value

    def _get_args(self):
        if isinstance(self.value, int):
            return [self.get_member_name()]
        return [self.value]

    def __eq__(self, other):
        if not isinstance(other, Quantifier):
            return NotImplemented
        return self.value == other.value

    def get_member_name(self) -> str | None:
        class MemberWrapper:
            def __init__(self, string):
                self.string = string

            def __repr__(self):
                return self.string

            def __str__(self):
                return self.string

        dct = self.__class__.__dict__
        for attr, value in dct.items():
            if (attr.isupper() and isinstance(value, int) and
                    self.value == value):
                return MemberWrapper(f"{self.__class__.__name__}.{attr}")


class Repetition(ArgsRepr):
    def __init__(self, beg, end=None):
        self.beg = int(beg)
        self.end = int(end) if end else None

    def _get_args(self):
        if self.end:
            return [self.beg, self.end]
        else:
            return [self.beg]

    def __eq__(self, other):
        if not isinstance(other, Repetition):
            return NotImplemented
        return (self.beg, self.end) == (other.beg, other.end)


class Char(ArgsRepr):
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
