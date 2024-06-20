from __future__ import annotations

from typing import Iterable


class TreeModifierWarning(Warning):
    def __init__(self, warnings: list[SemanticWarning]):
        self.warnings = warnings

    def __repr__(self):
        return f"TreeModifierWarning({self.warnings})"

    def __str__(self):
        return '\n'.join(self.warnings)


class SemanticWarning(Warning):
    pass


class LookaheadMetanameWarning(SemanticWarning):
    ...


class UnusedMetaRuleWarning(SemanticWarning):
    ...


class SemanticError(Exception):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value
        return NotImplemented


class GatheredSemanticErrors(Exception):
    def __init__(self, exceptions: Iterable[SemanticError]):
        self.exceptions = exceptions

    def __repr__(self):
        return f"GatheredSemanticErrors({self.exceptions})"

    def __str__(self):
        return '\n'.join(str(e) for e in self.exceptions)


class UndefEntryError(SemanticError):
    ...


class RedefEntryError(SemanticError):
    ...


class UndefRulesError(SemanticError):
    """Undefined rules error.

    Raised, when an identifier in the right-hand side of a rule not found
    in rule names set.

    Args:
        rules: A mapping from undefined identifier to the rule, where
            it was found.
    """


class RedefRulesError(SemanticError):
    """Raised when the rule with the same id is defined more than once.

    Args:
        rules: A dictionary that maps an identifier to a sequence
            of rules with this identifier.
    """


class UndefMetaRulesError(SemanticError):
    ...


class RedefMetaRulesError(SemanticError):
    ...


class MetanameRedefError(SemanticError):
    """Raised when metaname is redefined.

    Redefinition of the metaname will probably lead to compiler/interpreter
    errors (redefined variable) or at least to malfunctioning parser.
    """


class InvalidRangesError(SemanticError):
    ...


class InvalidRepetitionsError(SemanticError):
    ...



