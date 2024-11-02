from typing import Optional

from polygen.translator import Translator, Context, TranslationError
from polygen.visitor import GrammarPreVisitor, Context as Parents
from polygen.node import Rule


class UndefEntryError(TranslationError):
    critical = False

    def __init__(self):
        super().__init__("entry not defined")


class RedefEntryError(TranslationError):
    critical = False

    def __init__(self, prev_defined: Rule, redefined: Rule):
        super().__init__(
            "entry rule redefined: first defined at {}, redefined at {}")
        self.args = (prev_defined.parse_info, redefined.parse_info)


class FindEntryRule(Translator, GrammarPreVisitor):
    """Find the entry rule"""

    def __init__(self):
        self.entry: Optional[Rule] = None

    def translate(self, ctx: Context):
        self.visit(ctx.grammar, ctx)
        if self.entry is None:
            ctx.error(UndefEntryError())
        ctx.grammar.entry = self.entry

    def visit_Rule(self, node: Rule, parents: Parents, ctx: Context):
        if node.entry:
            self.entry = node
            return

        if self.entry is not None:
            ctx.error(RedefEntryError(self.entry, node))

