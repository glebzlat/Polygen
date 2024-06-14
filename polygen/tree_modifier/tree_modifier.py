from __future__ import annotations

from ..node import Grammar

from .errors import TreeModifierWarning, SemanticWarning

from .modifiers import (
    CheckUndefinedRules,
    CheckRedefinedRules,
    ReplaceNestedExprs,
    FindEntryRule,
    CreateAnyChar,
    IgnoreRules,
    GenerateMetanames,
    AssignMetaRules,
    ValidateNodes
)
from .leftrec import compute_lr


MODIFIERS = [
    FindEntryRule,
    ValidateNodes,
    CreateAnyChar,
    ReplaceNestedExprs,
    CheckUndefinedRules,
    CheckRedefinedRules,
    AssignMetaRules,
    IgnoreRules,
    GenerateMetanames,

    compute_lr
]


class TreeModifier:
    def __init__(self, modifiers):
        self.modifiers = modifiers
        self.warnings = []

    def apply(self, tree: Grammar):
        for m in self.modifiers:
            if callable(m):
                m(tree)
            else:
                while not m.done:
                    self._visit(tree, [], m)
                    m.apply()

        if self.warnings:
            raise TreeModifierWarning(self.warnings)

    def _visit(self, node, parents, modifier):
        parents.append(node)
        for child in node:
            self._visit(child, parents, modifier)
        parents.pop()
        self._visit_post(node, parents, modifier)

    def _visit_post(self, node, parents, modifier):
        node_type_name = type(node).__name__
        method_name = f"visit_{node_type_name}"
        visitor = getattr(modifier, method_name, None)
        if visitor is not None:
            try:
                visitor(node, parents)

            except SemanticWarning as warn:
                self.warnings.append(warn)
