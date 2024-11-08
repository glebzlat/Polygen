from collections import defaultdict
from enum import IntEnum

from polygen.translator import (
    Translator, Context, TranslationError, TranslationWarning
)
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import Id, Alt, MetaRef, MetaRule


class Stage(IntEnum):

    # AssignMetaRules works in two stages:
    #
    #   1) It iterates over the grammar visiting alternatives and collects
    #      references to metarules from them. On this stage it constructs a
    #      mapping Rule Id -> list of Alts that reference that rule
    #
    #   2) It iterates over the grammar visiting MetaRules. When it encounters
    #      a metarule, it checks if it is a named rule, if it appears in
    #      collected references, and if it is not already assigned. If all
    #      right, then it removes a reference from references and assigns the
    #      metarule to alts that reference it.

    COLLECT_REFS = 1
    ASSIGN_META = 2


class UndefMetaRule(TranslationError):
    critical = False

    def __init__(self, id: Id, alt: Alt):
        super().__init__("Undefined metarule {} at: {}")
        self.args = (id.value, alt.parse_info)


class RedefMetaRule(TranslationError):
    critical = False

    def __init__(self, id: Id, first_def: MetaRule, redef: MetaRule):
        super().__init__("Metarule {} previously defined at: {}, redefined: {}")
        self.args = (id.value, first_def.parse_info, redef.parse_info)


class UnusedMetaRule(TranslationWarning):

    def __init__(self, rule: MetaRule):
        super().__init__("Metarule {} unused at: {}", rule.id, rule.parse_info)


class AssignMetaRules(Translator, GrammarPostVisitor):
    """Find and assign metarules"""

    def __init__(self):

        # Alts that reference the metarule
        self.refs: defaultdict[Id, list[Alt]] = defaultdict(list)

        # Metarule ids that are assigned to alternatives
        self.assigned: set[Id] = set()

        # Store metarules to find duplicates
        self.metarules: defaultdict[Id, list[MetaRule]] = defaultdict(list)

        self.stage: Stage = Stage.COLLECT_REFS

    def translate(self, ctx: Context):
        self.visit(ctx.grammar, ctx)
        self.stage = Stage.ASSIGN_META
        self.visit(ctx.grammar, ctx)

        for ref in self.refs:
            for alt in self.refs[ref]:
                ctx.error(UndefMetaRule(ref, alt))

        dups = ((id, rules) for id, rules in self.metarules.items()
                if len(rules) > 1)
        for id, rules in dups:
            first_rule = rules[0]
            for i in range(1, len(rules)):
                ctx.error(RedefMetaRule(id, first_rule, rules[i]))

    def visit_Alt(self, node: Alt, parents: Parents, ctx: Context):
        if self.stage == Stage.COLLECT_REFS:
            if type(node.metarule) is MetaRef:
                self.refs[node.metarule.name].append(node)

    def visit_MetaRule(self, node: MetaRule, parents: Parents, ctx: Context):
        if self.stage != Stage.ASSIGN_META:
            return

        if type(parents[-1]) is Alt:
            # Inline metarule is already assigned
            return

        self.metarules[node.id].append(node)
        if node.id not in self.refs:
            # If the metarule does not appear in collected references,
            # it is either not referenced by any alternative or redefined.
            if node.id not in self.assigned:
                # The rule was not assigned, so it is unused
                ctx.warning(UnusedMetaRule(node))
            return

        self.assigned.add(node.id)
        alts = self.refs.pop(node.id)
        for alt in alts:
            alt.metarule = node
