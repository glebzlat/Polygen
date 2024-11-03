from collections import defaultdict

from polygen.translator import Translator, Context
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import Id, Rule, NamedItem


class IgnoreRules(Translator, GrammarPostVisitor):
    """Find rules marked as ignored and ignore all its references

    Collects rules with 'ignore' flag set and sets `NamedItem.IGNORE` value
    to the node names.
    """

    def __init__(self):
        self.ids: set[Id] = set()
        self.items: defaultdict[Id, list[NamedItem]] = defaultdict(list)

    def translate(self, ctx: Context):
        self.visit(ctx.grammar)

        for rule_id in self.ids:
            for i in self.items[rule_id]:
                if i.name is None:
                    i.name = Id(NamedItem.IGNORE)

    def visit_NamedItem(self, node: NamedItem, parents: Parents):
        inner = node.inner_item
        if isinstance(inner, Id):
            self.items[inner].append(node)

    def visit_Rule(self, node: Rule, parents: Parents):
        if node.ignore:
            self.ids.add(node.id)
