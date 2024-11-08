from polygen.translator import (
    Translator,
    Context,
    TranslationError,
    TranslationWarning
)
from polygen.modifier import (
    Options,
    TreeModifierWarning,
    SemanticError,
    ModifierVisitor,
    AssignMetaRules,
    ValidateRangesAndReps,
    ComputeLR
)


class ModifierError(TranslationError):
    critical = True


class ModifierWarning(TranslationWarning):
    pass


class InvokeModifier(Translator):

    def translate(self, ctx: Context):
        try:
            modifier = self.create_modifier(ctx.reserved_words)
            modifier.apply(ctx.grammar)
        except TreeModifierWarning as w:
            ctx.warning(ModifierWarning("{}", w))
        except SemanticError as e:
            ctx.error(ModifierError("{}", e))

    def create_modifier(self, reserved_words: set[str]) -> ModifierVisitor:
        modifier_classes = [
            AssignMetaRules,
            ValidateRangesAndReps,
            ComputeLR
        ]

        options = Options(reserved_words=reserved_words)
        modifiers = []
        for cls in modifier_classes:
            modifiers.append(cls(options))

        return ModifierVisitor(modifiers)

