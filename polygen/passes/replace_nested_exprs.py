from collections import Counter

from polygen.translator import Translator, Context
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import Id, Rule, Expr


class ReplaceNestedExprs(Translator, GrammarPostVisitor):

    def __init__(self):
        self.created_exprs: dict[Expr, Id] = {}
        self.id_count: Counter[Id] = Counter()

    def translate(self, ctx: Context):
        self.visit(ctx.grammar)

        rules = (Rule(id, expr) for expr, id in self.created_exprs.items())
        lst = Rule.from_iterable(rules)
        if lst:
            ctx.grammar.rules.end.emplace_after(lst)

    def visit_Expr(self, node: Expr, parents: Parents):
        if type(parents[-1]) is Rule:
            return

        if node in self.created_exprs:
            # We have already created rule with equivalent expression, so
            # just replace current expression by the reference to the rule
            parents[-1].item = self.created_exprs[node]
            return

        new_id = self.create_id(parents.rule.id)
        parents[-1].item = new_id

        self.created_exprs[node] = new_id

    def create_id(self, id: Id) -> Id:
        self.id_count[id] = idx = self.id_count[id] + 1
        return Id(f"{id.value}__GEN_{idx}")
