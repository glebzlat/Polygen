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

    def __init__(self, id: Id):
        super().__init__("undefined rule {} at {pos}", pos=id.parse_info)
        self.args = (id,)


class CheckUndefRules(Translator, GrammarPostVisitor):
    """Find rules that are referenced but have no definitions"""

    def __init__(self):
        self.ids: list[Id] = []
        self.rule_names: set[Id] = set()

    def translate(self, ctx: Context):
        self.visit(ctx.grammar)

        for i in self.ids:
            if i not in self.rule_names:
                ctx.error(UndefRuleError(i))

    def visit_Rule(self, node: Rule, parents: Parents):
        self.rule_names.add(node.id)

    def visit_Id(self, node: Id, parents: Parents):
        if type(parents[-1]) in (MetaRef, MetaRule):
            return
        self.ids.append(node)
