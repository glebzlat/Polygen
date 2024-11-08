from polygen.translator import Translator, Context, TranslationError
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import Repetition


class InvalidRepetition(TranslationError):
    critical = False

    def __init__(self, node: Repetition):
        super().__init__("Invalid repetition: {} at: {}", node, node.parse_info)


class ValidateReps(Translator, GrammarPostVisitor):
    """Check repetitions for correctness

    Repetition right boundary cannot be greater than the left boundary.
    """

    def translate(self, ctx: Context):
        self.visit(ctx.grammar, ctx)

    def visit_Repetition(
        self, node: Repetition, parents: Parents, ctx: Context
    ):
        if node.last is not None and node.last < node.first:
            ctx.error(InvalidRepetition(node))
