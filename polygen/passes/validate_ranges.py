from polygen.translator import Translator, Context, TranslationError
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import Range


class InvalidRange(TranslationError):
    critical = False

    def __init__(self, node: Range):
        super().__init__("Invalid range {} at: {}", node, node.parse_info)


class ValidateRanges(Translator, GrammarPostVisitor):
    """Check range correctness

    Range cannot have right boundary less than the left boundary. Range `[z-a]`
    considered incorrect.
    """

    def translate(self, ctx: Context):
        self.visit(ctx.grammar, ctx)

    def visit_Range(self, node: Range, parents: Parents, ctx: Context):
        if node.last and node.last < node.first:
            ctx.error(InvalidRange(node))
