from enum import StrEnum


class Errors(StrEnum):
    INVALID_RANGE = "invalid-range"
    INVALID_REPETITION = "invalid-rep"
    UNDEF_RULES = "undef-rules"
    REDEF_RULES = "redef-rules"


class Warnings(StrEnum):
    UNUSED_RULES = "unused-rules"


class TreeTransformerError(Exception):
    def __init__(self, what: Errors, *nodes):
        self.what = what
        self.nodes = nodes


class TreeTransformerWarning(Warning):
    def __init__(self, what: Warnings, *nodes):
        self.what = what
        self.nodes = nodes
