from polygen.translator import Translator, Context
from polygen.visitor import GrammarPreVisitor, Context as Parents
from polygen.node import (
    DLL,
    Rule,
    Id,
    Expr,
    Alt,
    NamedItem,
    Class,
    Range,
    String,
    Char,
    AnyChar
)


class CreateAnyChar(Translator, GrammarPreVisitor):
    """Create artificial rule for AnyChar

    Creates AnyChar rule, whose expression is a character class composed of
    all characters seen in the grammar, and replaces all occurences of AnyChar
    node by the reference to the rule.
    """

    def __init__(self):
        self.chars: set[Char] = set()
        self.rule_id = Id("AnyChar__GEN")

    def translate(self, ctx: Context):
        self.visit(ctx.grammar)

        cls = charset_to_class(self.chars)
        rule = Rule(self.rule_id, Expr([Alt([NamedItem(None, cls)])]))
        if DLL.length(ctx.grammar.rules):
            ctx.grammar.rules.end.insert_after(rule)

    def visit_Char(self, node: Char, parents: Parents):
        self.chars.add(node)

    def visit_Range(self, node: Range, parents: Parents):
        self.chars |= range_to_chars(node)

    def visit_String(self, node: String, parents: Parents):
        self.chars.update(DLL.astuple(node.chars))

    def visit_AnyChar(self, node: AnyChar, parents: Parents):
        parents[-1].item = self.rule_id


def charset_to_class(chars: set[Char]) -> Class:
    """Create class of ranges from the set of characters."""
    ranges = []
    prev = None

    for c in sorted(chars):
        if not prev:
            ranges.append(Range(c, None))
            prev = c
            continue
        if c.code - prev.code != 1:
            ranges[-1].last = prev
            ranges.append(Range(c, None))
        prev = c

    return Class(ranges)


def range_to_chars(rng: Range) -> set[Char]:
    if rng.last is None:
        return {rng.first}
    return set(map(Char, range(ord(rng.first.chr), ord(rng.last.chr) + 1)))
