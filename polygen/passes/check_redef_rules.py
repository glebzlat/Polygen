from collections import defaultdict

from polygen.translator import Translator, Context, TranslationError
from polygen.visitor import Context as Parents
from polygen.node import Id, Rule


class RedefRuleError(TranslationError):

    def __init__(self, first_defined: Rule, redefined: Rule):
        super().__init__("redefined rule {} at {}, first defined at {}")
        self.args = (
            redefined.id, redefined.parse_info, first_defined.parse_info)


class CheckRedefRules(Translator):

    def __init__(self):
        self.rules: defaultdict[Id, list[Rule]] = defaultdict(list)

    def translate(self, ctx: Context):
        self.visit(ctx.grammar)

        for id, rules in self.rules.items():
            for i in range(1, len(rules)):
                ctx.error(RedefRuleError(rules[0], rules[i]))

    def visit_Rule(self, node: Rule, parents: Parents):
        self.rules[node.id].append(node)
