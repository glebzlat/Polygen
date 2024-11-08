from collections import defaultdict

from polygen.translator import (
    Translator,
    Context,
    TranslationWarning
)
from polygen.visitor import GrammarPostVisitor, Context as Parents
from polygen.node import (
    Id,
    Alt,
    And,
    Not,
    NamedItem,
)


class MetanameWarning(TranslationWarning):

    def __init__(self, name: str, node: NamedItem):
        super().__init__("Metaname {} cannot be assigned to a node: {}")
        self.node = node
        self.name = name
        self.args = (self.name, self.node.parse_info)


class ReservedWordWarning(TranslationWarning):

    def __init__(self, metaname: str, new_metaname: str, node: NamedItem):
        super().__init__(
            "Metaname hinders reserved word: {} and is changed to {} at {}")
        self.args = (metaname, new_metaname, node.parse_info)


class MetanameRedefWarning(TranslationWarning):

    def __init__(self, metaname: str, redef: NamedItem, last: NamedItem):
        super().__init__(
            "Metaname {} redefined at: {}, previosly defined at {}")
        self.args = (metaname, redef.parse_info, last.parse_info)


class GenerateMetanames(Translator, GrammarPostVisitor):
    """Generate node metanames

    Metanames created as follows.

    - If the user has assigned a metaname, it is checked if the metaname
      clashes with previosly defined names or with reserved words. If so, then
      the metaname prepended with an underscore and warning is emerged.

    - If the user has assigned a metaname to a lookahead node, then metaname
      is discarded and MetanameWarning is emerged.

    - If the node is unnamed and is a nonterminal, that is, contains rule
      identifier, then the metaname is derived from identifier's name. If such
      metaname clashes with a reserved word or already was defined, then it is
      silently prepended with an underscore.

    - Node is unnamed and is a terminal, that is, contains node without name.
      In this case metaname is created by prepending current terminal node's
      number by an underscore: `_{idx}`.

    Terminal node indexes and metaname definitions are local to each
    alternative.
    """

    def __init__(self):
        self.metanames: defaultdict[str, list[NamedItem]] = defaultdict(list)
        self.index = 0

        self.unnamed = "<unnamed>"

    def translate(self, ctx: Context):
        self.visit(ctx.grammar, ctx)

    def visit_NamedItem(self, node: NamedItem, parents: Parents, ctx: Context):
        metaname = node.name.value if node.name is not None else None

        if metaname is not None:
            # Name is assigned by user
            if metaname == NamedItem.IGNORE:
                return

            if type(node.item) in (And, Not):
                ctx.warning(MetanameWarning(metaname, node))
                node.name = NamedItem.IGNORE
                return

            if metaname in self.metanames:
                ctx.warning(MetanameRedefWarning(
                    metaname, node, self.metanames[node][-1]))
                metaname = f"_{metaname}"

            if metaname in ctx.reserved_words:
                new_metaname = f"_{metaname}"
                ctx.warning(ReservedWordWarning(metaname, new_metaname, node))
                metaname = new_metaname

        if type(node.item) in (And, Not):
            metaname = NamedItem.IGNORE

        elif isinstance(node.inner_item, Id):
            # Nonterminal - derive metaname from identifier
            name = node.inner_item.value

            if "__GEN" in name:
                # Assign index to generated nonterminals
                self.index += 1
                metaname = f"_{self.index}"

            else:
                metaname = name.lower()
                if metaname in ctx.reserved_words:
                    metaname = f"_{metaname}"

                # Append index if there were items with same name
                idx = len(self.metanames[metaname])
                if idx:
                    metaname = f"{metaname}{idx}"

        else:
            # Terminal - has no identifier
            self.index += 1
            metaname = f"_{self.index}"

        node.name = Id(metaname)
        self.metanames[metaname].append(node)

    def visit_Alt(self, node: Alt, parents: Parents, ctx: Context):
        self.index = 0
        self.metanames.clear()
