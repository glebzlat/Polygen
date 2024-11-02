from collections import defaultdict

from polygen.translator import Translator, Context, TranslationError
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import (
    Id,
    Rule,
    MetaRef,
    MetaRule
)


class UndefRuleError(TranslationError):
    critical = False

    def __init__(self, rule: Rule):
        super().__init__("undefined rule {} with id {}")
        self.args = (rule.id, rule)


class CheckUndefRules(Translator, GrammarPostVisitor):
    """Find rules that are referenced but have no definitions"""

    def __init__(self):
        self.named_items: defaultdict[Id, list[Rule]] = defaultdict(list)
        self.rule_names: set[Id] = set()

    def translate(self, ctx: Context):
        self.visit(ctx.grammar)

        if diff := set(self.named_items) - self.rule_names:
            for i in diff:
                for r in self.named_items[i]:
                    ctx.error(UndefRuleError(r))

    def visit_Rule(self, node: Rule, parents: Parents):
        self.rule_names.add(node.id)
        self._visit(node.expr, parents)

    def visit_Id(self, node: Id, parents: Parents):
        if type(parents[-1]) in (MetaRef, MetaRule):
            return
        self.named_items[node].append(parents.rule)
