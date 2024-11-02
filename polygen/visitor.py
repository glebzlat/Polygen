from typing import Any, Optional
from abc import abstractmethod

from polygen.node import Grammar, Rule, Alt, NamedItem


class Context:

    def __init__(self):
        self.stack = []
        self.grammar: Optional[Grammar] = None
        self.rule: Optional[Rule] = None
        self.alt: Optional[Alt] = None
        self.named_item: Optional[NamedItem] = None

    def __getitem__(self, idx: int):
        return self.stack[idx]

    def __len__(self) -> int:
        return len(self.stack)

    def append(self, node):
        if isinstance(node, Grammar):
            self.grammar = node
        elif isinstance(node, Rule):
            self.rule = node
        elif isinstance(node, Alt):
            self.alt = node
        elif isinstance(node, NamedItem):
            self.named_item = node

        self.stack.append(node)

    def pop(self, idx: int = -1):
        node = self.stack.pop(idx)

        if isinstance(node, Grammar):
            self.grammar = None
        elif isinstance(node, Rule):
            self.rule = None
        elif isinstance(node, Alt):
            self.alt = None
        elif isinstance(node, NamedItem):
            self.named_item = None

        return node


class GrammarVisitor:
    """Grammar tree visitor

    Visitor keeps track of nodes between the root of the tree and the node
    currently being visited. Classes that inherit from this class should
    define methods with the name `visit_<node-type>` to subscribe to certain
    node type. Nodes, which type name does not match any `visit_` method are
    passed.
    """

    def visit(self, node, *args: Any, **kwargs: Any) -> Any:
        ctx = Context()
        return self._visit(node, ctx, *args, **kwargs)

    @abstractmethod
    def _visit(self, node, ctx: Context, *args: Any, **kwargs: Any) -> Any:
        """Visit a node."""

    @abstractmethod
    def generic_visit(
        self, node, ctx: Context, *args: Any, **kwargs: Any
    ) -> None:
        ...


class GrammarPreVisitor(GrammarVisitor):

    def _visit(self, node, ctx: Context, *args: Any, **kwargs: Any) -> Any:
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.generic_visit)

        ctx.append(node)
        result = visitor(node, ctx, *args, **kwargs)
        ctx.pop()

        return result

    def generic_visit(
        self, node, ctx: Context, *args: Any, **kwargs: Any
    ) -> None:
        for value in node:
            self._visit(value, ctx, *args, **kwargs)


class GrammarPostVisitor(GrammarVisitor):

    def _visit(self, node, ctx: Context, *args: Any, **kwargs: Any) -> Any:
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.generic_visit)

        ctx.append(node)
        for value in node:
            self._visit(value, ctx, *args, **kwargs)
        ctx.pop()
        result = visitor(node, ctx, *args, **kwargs)

        return result

    def generic_visit(
        self, node, ctx: Context, *args: Any, **kwargs: Any
    ) -> None:
        pass
