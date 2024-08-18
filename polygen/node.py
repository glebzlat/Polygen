from __future__ import annotations

from typing import Iterable, Optional, TypeVar, Union, Iterator, Any
from itertools import zip_longest

from .utility import code_to_char, wrap_string


DoublyLinked = TypeVar("DoublyLinked", bound="DLL")


class DLL:
    """Doubly linked list"""

    left: Optional[DoublyLinked] = None
    right: Optional[DoublyLinked] = None

    @classmethod
    def from_iterable(cls, it: Iterable[DoublyLinked]) -> DoublyLinked | None:
        """Create a linked list from a sequence."""
        it = iter(it)
        node = head = next(it, None)
        if node is None:
            return None
        for n in it:
            node.insert_after(n)
            node = n
        return head

    def insert_after(self, node: DoublyLinked):
        """Add a single node after this node.

        Node will be removed from the list it is part of before being
        inserted into the new list.
        """
        node.remove()
        if self.right is not None:
            self.right.left = node
            node.right = self.right
        node.left = self
        self.right = node

    def insert_before(self, node: DoublyLinked):
        """Add a single node before this node.

        Node will be removed from the list it is part of before being
        inserted into the new list.
        """
        node.remove()
        if self.left is not None:
            self.left.right = node
            node.left = self.left
        node.right = self
        self.left = node

    def emplace_after(self, node: DoublyLinked):
        """Insert a list after this node

        If the node is a part of a list, then the whole list (from beginning
        to end) will be inserted.
        """
        if self.right is not None:
            end = node.end
            self.right.left = end
        beg = node.begin
        beg.left = self
        self.right = beg

    def emplace_before(self, node: DoublyLinked):
        """Insert a list before this node

        If the node is a part of a list, then the whole list (from beginning
        to end) will be inserted.
        """
        if self.left is not None:
            beg = node.begin
            self.left.right = beg
        end = node.end
        end.right = self
        self.left = end

    def forward(self) -> Iterator[DoublyLinked]:
        """Iterate the linked list forward (to the right)."""
        n = self
        while n is not None:
            yield n
            n = n.right

    def backward(self) -> Iterator[DoublyLinked]:
        """Iterate the linked list backward (to the left)."""
        n = self
        while n is not None:
            yield n
            n = n.left

    def replace(self, node: DoublyLinked):
        """Replace current node in the list by the new node."""
        if self.left is not None:
            self.left.right = node
        if self.right is not None:
            self.right.left = node

    def remove(self):
        """Remove this node from the list."""
        prev = self.left
        if self.left is not None:
            self.left.right = self.right
        if self.right is not None:
            self.right.left = prev

    @property
    def begin(self) -> DoublyLinked:
        """Get the head node of a list."""
        n = self
        while n.left is not None:
            n = n.left
        return n

    @property
    def end(self) -> DoublyLinked:
        """Get the last node of a list."""
        n = self
        while n.right is not None:
            n = n.right
        return n

    def iter(self, *, forward: bool = True) -> DoublyLinked:
        node = self
        if forward:
            while node is not None:
                yield node
                node = node.right
        else:
            while node is not None:
                yield node
                node = node.left

    def length(self) -> int:
        """Get the length of the list [self; end]."""
        return sum(1 for _ in DLL.forward(self))

    def astuple(self) -> tuple[DoublyLinked, ...] | tuple[()]:
        """Convert doubly linked list into a tuple of its elements."""
        return tuple(DLL.forward(self))


class GrammarVisitor:
    # taken from pegen
    # https://github.com/we-like-parsers/pegen/blob/main/src/pegen/grammar.py

    def visit(self, node, *args: Any, **kwargs: Any) -> Any:
        """Visit a node."""
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node, *args: Any, **kwargs: Any) -> None:
        for value in node:
            self.visit(value, *args, **kwargs)


class ParseInfo:
    start: int
    end: int
    line: int
    filename: str

    def __init__(self, arg):
        if isinstance(arg, list):
            assert arg
            self.start, self.end = arg[0].start, arg[-1].end
            self.line, self.filename = arg[0].line, arg[0].filename
        else:
            self.start, self.end = arg.start, arg.end
            self.line, self.filename = arg.line, arg.filename

    def __str__(self):
        return f"{self.filename}: line {self.line}: {self.start}"


class Grammar:
    def __init__(self,
                 rules: Iterable[Rule],
                 metarules: Optional[Iterable[MetaRule]] = None,
                 includes: Optional[Iterable[Include]] = None,
                 parse_info: Optional[ParseInfo] = None):

        self.rules: Optional[Rule] = DLL.from_iterable(rules)

        if metarules is not None:
            metarules = DLL.from_iterable(metarules)
        self.metarules: Optional[MetaRule] = metarules

        if includes is not None:
            includes = DLL.from_iterable(includes)
        self.includes = includes

        self.entry: Rule | None = None
        self.parse_info = parse_info

    def __repr__(self):
        lines = ["Grammar("]
        lines.append("  [")
        for rule in DLL.forward(self.rules):
            lines.append(f"    {repr(rule)},")
        lines.append("  ],")
        if self.metarules:
            lines.append("  [")
            for rule in DLL.forward(self.metarules):
                lines.append(f"    {repr(rule)},")
            lines.append("  ]")
        else:
            lines.append("[]")
        lines.append(")")
        return '\n'.join(lines)

    def __str__(self):
        rules = (str(rule) for rule in DLL.forward(self.rules))
        metarules = (str(rule) for rule in DLL.forward(self.metarules))
        return '\n'.join(rules) + '\n\n' + '\n\n'.join(metarules)

    def __iter__(self) -> Iterable[Rule]:
        yield from (*DLL.forward(self.rules), *DLL.forward(self.metarules))

    def __eq__(self, other):
        if type(other) is Grammar:
            astuple = DLL.astuple
            return (
                (astuple(self.rules), astuple(self.metarules), self.entry) ==
                (astuple(other.rules), astuple(other.metarules), other.entry))
        return NotImplemented

    def __hash__(self):
        return hash(tuple(self.rules))

    def merge(self, grammar: Grammar):
        if grammar.rules:
            if self.rules:
                self.rules.emplace_before(grammar.rules)
                self.rules = self.rules.begin
            else:
                self.rules = grammar.rules
        if grammar.metarules:
            if self.metarules:
                self.metarules.emplace_before(grammar.metarules)
                self.metarules = self.metarules.begin
            else:
                self.metarules = grammar.metarules
        if grammar.includes:
            if self.includes:
                self.includes.emplace_before(grammar.includes)
                self.includes = self.includes.begin
            else:
                self.includes = grammar.includes


class Include(DLL):
    def __init__(self, path: str, line: int, filename: str):
        self.path = path
        self.line = line
        self.filename = filename

    def __repr__(self):
        return f"Include({self.path!r}, {self.line}, {self.filename!r})"

    def __str__(self):
        return repr(self)


class Rule(DLL):
    def __init__(self,
                 id: Id,
                 expr: Expr,
                 parse_info: Optional[ParseInfo] = None,
                 *,
                 ignore: bool = False,
                 entry: bool = False):

        self.id = id
        self.expr = expr
        self.ignore = ignore
        self.entry = entry
        self.head = False
        self.leftrec: Optional[LR] = None
        self.nullable = False
        self.parse_info = parse_info

    def __str__(self):
        entry = "@entry\n" if self.entry else ""
        ignore = "@ignore\n" if self.ignore else ""
        return f"{entry}{ignore}{self.id} <- {self.expr}"

    def __repr__(self):
        parts = [repr(self.id), repr(self.expr)]
        if self.ignore:
            parts.append("ignore=True")
        if self.entry:
            parts.append("entry=True")
        args = ', '.join(parts)
        return f"Rule({args})"

    def __iter__(self):
        yield self.expr

    def __eq__(self, other):
        if type(other) is Rule:
            return (self.id, self.expr) == (other.id, other.expr)
        return NotImplemented

    def __hash__(self):
        return hash((self.id, self.expr))


class LR:
    def __init__(self, chains: list[tuple[Id]]):
        self.chains = chains

    def __repr__(self):
        return f"LR({self.chains!r})"

    def __str__(self):
        lines = []
        for chain in self.chains:
            tail = chain[0]
            lines.append(' -> '.join(str(i) for i in (*chain, tail)))
        return '\n'.join(lines)

    @property
    def heads(self):
        yield from (c[0] for c in self.chains)

    def copy(self):
        return LR(self.chains)


class MetaRef:
    def __init__(self, name: Id, parse_info: Optional[ParseInfo] = None):
        self.name = name
        self.parse_info = parse_info

    def __repr__(self):
        return f"MetaRef({self.name!r})"

    def __str__(self):
        return f"${self.name}"

    def __iter__(self):
        yield self.name

    def __eq__(self, other):
        if type(other) is MetaRef:
            return self.name == other.name
        return NotImplemented

    def __hash__(self):
        return hash(self.name)


class MetaRule(DLL):
    def __init__(self,
                 id: Optional[Id],
                 expr: str,
                 parse_info: Optional[ParseInfo] = None):

        self.id = id
        self.expr = expr
        self.parse_info = parse_info

    def __repr__(self):
        return f"MetaRule({self.id!r}, {self.expr!r})"

    def __str__(self):
        if self.id is None:
            return f"{{{self.expr}}}"
        return f"${self.id} {{{self.expr}}}"

    def __iter__(self):
        yield self.id

    def __eq__(self, other):
        if type(other) is MetaRule:
            return self.id == other.id
        return NotImplemented

    def __hash__(self):
        return hash(self.id)


class Expr:
    def __init__(self,
                 alts: Iterable[Alt],
                 parse_info: Optional[ParseInfo] = None):

        self.alts: Optional[Alt] = DLL.from_iterable(alts)
        self.parse_info = parse_info

    def __repr__(self):
        alts = ', '.join(repr(alt) for alt in DLL.forward(self.alts))
        return f"Expr([{alts}])"

    def __str__(self):
        return ' / '.join(str(alt) for alt in DLL.forward(self.alts))

    def __iter__(self):
        yield from DLL.forward(self.alts)

    def __eq__(self, other):
        if type(other) is Expr:
            return DLL.astuple(self.alts) == DLL.astuple(other.alts)
        return NotImplemented

    def __hash__(self):
        return hash(tuple(DLL.forward(self.alts)))


class Alt(DLL):
    def __init__(self,
                 items: Iterable[NamedItem],
                 parse_info: Optional[ParseInfo] = None,
                 *,
                 metarule: MetaRef | MetaRule | None = None):

        self.items: Optional[NamedItem] = DLL.from_iterable(items)
        self.metarule = metarule
        self.nullable = False
        self.parse_info = parse_info
        self.grower = False

    def __repr__(self):
        items = ', '.join(repr(i) for i in DLL.forward(self.items))
        metarule = "" if self.metarule is None else f", {self.metarule!r}"
        return f"Alt([{items}]{metarule})"

    def __str__(self):
        items = ' '.join(str(i) for i in DLL.forward(self.items))
        if self.metarule:
            return ' '.join((items, str(self.metarule)))
        return items

    def __iter__(self):
        yield from DLL.forward(self.items)

    def __eq__(self, other):
        if type(other) is Alt:
            return ((DLL.astuple(self.items), self.metarule) ==
                    (DLL.astuple(other.items), other.metarule))
        return NotImplemented

    def __hash__(self):
        return hash((self.metarule, self.items))


class NamedItem(DLL):

    IGNORE = "_"

    def __init__(self,
                 name: Optional[Id],
                 item: Item,
                 parse_info: Optional[ParseInfo] = None):

        self.name = name
        self.item = item

        assert type(self.item) is not NamedItem

        self.nullable = False
        self.parse_info = parse_info

    @property
    def inner_item(self) -> Item | str:
        i = self.item
        while islookahead(i) or isquant(i):
            i = i.item
        return i

    def __repr__(self):
        return f"NamedItem({self.name!r}, {self.item!r})"

    def __str__(self):
        if self.name:
            return f"{self.name}:{self.item}"
        return str(self.item)

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if type(other) is NamedItem:
            return (self.name, self.item) == (other.name, other.item)
        return NotImplemented

    def __hash__(self):
        return hash((self.name, self.item))


class Id:
    def __init__(self, value: str, parse_info: Optional[ParseInfo] = None):
        self.value = value
        self.parse_info = parse_info

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"Id({self.value!r})"

    def __iter__(self):
        yield from ()

    def __eq__(self, other):
        if type(other) is Id:
            return self.value == other.value
        return NotImplemented

    def __lt__(self, other):
        if type(other) is Id:
            return self.value < other.value
        return NotImplemented

    def __hash__(self):
        return hash(self.value)


class String:
    def __init__(self,
                 chars: Iterable[Char],
                 parse_info: Optional[ParseInfo] = None):
        self.chars: Optional[Char] = DLL.from_iterable(chars)
        self.parse_info = parse_info

    def __repr__(self):
        chars = ', '.join(repr(c) for c in DLL.forward(self.chars))
        return f"String([{chars}])"

    def __str__(self):
        chars = ''.join(c.chr for c in DLL.forward(self.chars))
        return wrap_string(chars, "double")

    def __iter__(self):
        yield from DLL.forward(self.chars)

    def __eq__(self, other):
        if isinstance(other, String):
            return DLL.astuple(self.chars) == DLL.astuple(other.chars)
        return NotImplemented

    def __lt__(self, other):
        if type(other) is not String:
            return NotImplemented
        for a, b in zip_longest(DLL.forward(self.chars),
                                DLL.forward(other.chars)):
            if b is None or a >= b:
                return False
        return True

    def __hash__(self):
        return hash(DLL.astuple(self.chars))


class Char(DLL):
    def __init__(self,
                 code: int | str,
                 parse_info: Optional[ParseInfo] = None):

        if isinstance(code, str):
            code = ord(code)
        self.code = code
        self.parse_info = parse_info

    def __repr__(self):
        return f"Char({str(self)})"

    def __str__(self):
        return wrap_string(self.chr, 'single')

    @property
    def chr(self):
        char = code_to_char(self.code)
        if char == '\\':
            return '\\\\'
        return char

    def __iter__(self):
        yield from ()

    def __eq__(self, other):
        if type(other) is Char:
            return self.code == other.code
        return NotImplemented

    def __lt__(self, other):
        if type(other) is Char:
            return self.code < other.code
        return NotImplemented

    def __hash__(self):
        return hash(self.code)


class AnyChar:
    def __init__(self, parse_info: Optional[ParseInfo] = None):
        self.parse_info = parse_info

    def __repr__(self):
        return "AnyChar()"

    def __str__(self):
        return "."

    def __iter__(self):
        yield from ()

    def __eq__(self, other):
        return isinstance(other, AnyChar)

    def __hash__(self):
        return hash('.')


class Class:
    def __init__(self,
                 ranges: Iterable[Range],
                 parse_info: Optional[ParseInfo] = None):
        self.ranges: Optional[Range] = DLL.from_iterable(ranges)
        self.parse_info = parse_info

    def __repr__(self):
        ranges = ', '.join(repr(r) for r in DLL.forward(self.ranges))
        return f"Class([{ranges}])"

    def __str__(self):
        ranges = ''.join(str(r) for r in DLL.forward(self.ranges))
        return f"[{ranges}]"

    def __iter__(self):
        yield from DLL.forward(self.ranges)

    def __eq__(self, other):
        if isinstance(other, Class):
            return DLL.astuple(self.ranges) == DLL.astuple(self.ranges)
        return NotImplemented

    def __hash__(self):
        return hash(DLL.astuple(self.ranges))


class Range(DLL):
    def __init__(self,
                 first: Char,
                 last: Optional[Char] = None,
                 parse_info: Optional[ParseInfo] = None):
        self.first = first
        self.last = last
        self.parse_info = parse_info

    def __repr__(self):
        return f"Range({self.first!r}, {self.last!r})"

    def __str__(self):
        if self.last is not None:
            return f"{self.first.chr}-{self.last.chr}"
        return self.first.chr

    def __iter__(self):
        if self.last is None:
            yield self.first
        else:
            yield from (self.first, self.last)

    def __eq__(self, other):
        if isinstance(other, Range):
            return (self.first, self.last) == (other.first, other.last)
        return NotImplemented

    def __hash__(self):
        return hash((self.first, self.last))


class ZeroOrOne:
    def __init__(self, item: Item, parse_info: Optional[ParseInfo] = None):
        self.item = item
        self.parse_info = parse_info

    def __repr__(self):
        return f"ZeroOrOne({self.item!r})"

    def __str__(self):
        return f"{self.item}?"

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if isinstance(other, ZeroOrOne):
            return self.item == other.item
        return NotImplemented

    def __hash__(self):
        return hash(self.item)


class ZeroOrMore:
    def __init__(self, item: Item, parse_info: Optional[ParseInfo] = None):
        self.item = item
        self.parse_info = parse_info

    def __repr__(self):
        return f"ZeroOrMore({self.item!r})"

    def __str__(self):
        return f"{self.item}*"

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if isinstance(other, ZeroOrMore):
            return self.item == other.item
        return NotImplemented

    def __hash__(self):
        return hash(self.item)


class OneOrMore:
    def __init__(self, item: Item, parse_info: Optional[ParseInfo] = None):
        self.item = item
        self.parse_info = parse_info

    def __repr__(self):
        return f"OneOrMore({self.item!r})"

    def __str__(self):
        return f"{self.item}+"

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if isinstance(other, OneOrMore):
            return self.item == other.item
        return NotImplemented

    def __hash__(self):
        return hash(self.item)


class Repetition:
    def __init__(self,
                 item: Item,
                 first: int,
                 last: Optional[int] = None,
                 parse_info: Optional[ParseInfo] = None):
        self.item = item
        self.first = first
        self.last = last
        self.parse_info = parse_info

    def __repr__(self):
        return f"Repetition({self.item!r}, {self.first}, {self.last})"

    def __str__(self):
        if self.last is not None:
            rep = f"{{{self.first},{self.last}}}"
        else:
            rep = f"{{{self.first}}}"
        return f"{self.item}{rep}"

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if type(other) is Repetition:
            return ((self.item, self.first, self.last)
                    == (other.item, other.first, other.last))
        return NotImplemented

    def __hash__(self):
        return hash((self.item, self.first, self.last))


class Not:
    def __init__(self, item: Item, parse_info: Optional[ParseInfo] = None):
        self.item = item
        self.parse_info = parse_info

    def __repr__(self):
        return f"Not({self.item!r})"

    def __str__(self):
        return f"!{self.item}"

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if isinstance(other, Not):
            return self.item == other.item
        return NotImplemented

    def __hash__(self):
        return hash(self.item)


class And:
    def __init__(self, item: Item, parse_info: Optional[ParseInfo] = None):
        self.item = item
        self.parse_info = parse_info

    def __repr__(self):
        return f"And({self.item!r})"

    def __str__(self):
        return f"&{self.item}"

    def __iter__(self):
        yield self.item

    def __eq__(self, other):
        if isinstance(other, And):
            return self.item == other.item
        return NotImplemented

    def __hash__(self):
        return hash(self.item)


def isquant(node: object) -> bool:
    """Return True if an object is quantifier, False otherwise."""
    return type(node) in (ZeroOrOne, ZeroOrMore, OneOrMore, Repetition)


def islookahead(node: object) -> bool:
    """Return True if an object is predicate, False otherwise."""
    return type(node) in (Not, And)


Item = Union[NamedItem, Id, Expr, Char, AnyChar, String, And, Not, ZeroOrOne,
             ZeroOrMore, OneOrMore]
