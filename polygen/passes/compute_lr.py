import logging

from typing import TypeVar, Hashable, Iterator
from collections import OrderedDict

from polygen.translator import Translator, Context
from polygen.visitor import (
    GrammarPreVisitor, GrammarPostVisitor, Context as Parents
)
from polygen.node import (
    Grammar,
    Rule,
    LR,
    MetaRule,
    Expr,
    Alt,
    NamedItem,
    Id,
    Not,
    And,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    String,
    Char,
    AnyChar,
    Class
)

logger = logging.getLogger("polygen.passes.compute_lr")


class NullableVisitor(Translator, GrammarPreVisitor):

    def translate(self, ctx: Context):
        ctx["visited"] = set()
        ctx["nullables"] = set()

        self.visit(ctx.grammar, ctx)

        ctx["visited"].clear()
        self.visit(ctx.grammar, ctx)

        del ctx["visited"]
        del ctx["nullables"]

    def visit_Grammar(self, node: Grammar, parents: Parents, ctx: Context):
        for r in node:
            self._visit(r, parents, ctx)

    def visit_Rule(self, node: Rule, parents: Parents, ctx: Context) -> bool:
        if node.id in ctx["visited"]:
            return False
        ctx["visited"].add(node.id)
        if self._visit(node.expr, parents, ctx):
            node.nullable = True
            ctx["nullables"].add(node.id)
        return node.nullable

    def visit_Expr(self, node: Expr, parents: Parents, ctx: Context) -> bool:
        for alt in node:
            if self._visit(alt, parents, ctx):
                return True
        return False

    def visit_Alt(self, node: Alt, parents: Parents, ctx: Context) -> bool:
        for i in node:
            if not self._visit(i, parents, ctx):
                return False
        node.nullable = True
        return True

    def visit_NamedItem(
        self, node: NamedItem, parents: Parents, ctx: Context
    ) -> bool:
        if self._visit(node.item, parents, ctx):
            node.nullable = True
        return node.nullable

    def visit_Id(self, node: Id, parents: Parents, ctx: Context) -> bool:
        return node in ctx["nullables"]

    def visit_Not(self, node: Not, parents: Parents, ctx: Context) -> bool:
        return True

    def visit_And(self, node: And, parents: Parents, ctx: Context) -> bool:
        return True

    def visit_ZeroOrOne(
        self, node: ZeroOrOne, parents: Parents, ctx: Context
    ) -> bool:
        return True

    def visit_ZeroOrMore(
        self, node: ZeroOrMore, parents: Parents, ctx: Context
    ) -> bool:
        return True

    def visit_OneOrMore(
        self, node: OneOrMore, parents: Parents, ctx: Context
    ) -> bool:
        return False

    def visit_Repetition(
        self, node: Repetition, parents: Parents, ctx: Context
    ) -> bool:
        return node.first == 0

    def visit_String(
        self, node: String, parents: Parents, ctx: Context
    ) -> bool:
        return not node.chars

    def visit_Char(self, node: Char, parents: Parents, ctx: Context) -> bool:
        return False

    def visit_AnyChar(
        self, node: AnyChar, parents: Parents, ctx: Context
    ) -> bool:
        return False

    def visit_Class(self, node: Class, parents: Parents, ctx: Context) -> bool:
        return not node.ranges


class FirstGraphVisitor(Translator, GrammarPreVisitor):

    def translate(
        self, ctx: Context
    ) -> tuple[dict[Id, list[Id]], dict[Id, Rule]]:
        return self.visit(ctx.grammar)

    def visit_Grammar(self, node: Grammar, parents: Parents):
        graph: dict[Id, list[Id]] = {}
        rules: dict[Id, Rule] = {}

        for r in node:
            if isinstance(r, MetaRule):
                continue
            key, val = self._visit(r, parents)
            graph[key] = val
            rules[key] = r

        if logger.isEnabledFor(logging.INFO):
            lines = []
            for k, v in graph.items():
                if not v:
                    continue
                strs = ', '.join(str(i) for i in v)
                lines.append(f"  {k}: [{strs}]")
            logger.info("first graph:\n%s", '\n'.join(lines))

        return graph, rules

    def visit_Rule(self, node: Rule, parents: Parents):
        return node.id, self._visit(node.expr, parents)

    def visit_Expr(self, node: Expr, parents: Parents):
        names, added = [], set()
        for n in node:
            for n in self._visit(n, parents):
                if n in added:
                    continue
                names.append(n)
                added.add(n)
        return names

    def visit_Alt(self, node: Alt, parents: Parents):
        names, added = [], set()
        for i in node:
            assert type(i) is NamedItem
            for n in (self._visit(i, parents) or []):
                if n in added:
                    continue
                names.append(n)
                added.add(n)
            if not i.nullable:
                break
        return names

    def visit_NamedItem(self, node: NamedItem, parents: Parents):
        return self._visit(node.item, parents)

    def visit_ZeroOrOne(self, node: ZeroOrOne, parents: Parents):
        return self._visit(node.item, parents)

    def visit_ZeroOrMore(self, node: ZeroOrMore, parents: Parents):
        return self._visit(node.item, parents)

    def visit_OneOrMore(self, node: OneOrMore, parents: Parents):
        return self._visit(node.item, parents)

    def visit_Id(self, node: Id, parents: Parents):
        return [node]

    def visit_String(self, node: String, parents: Parents):
        return []

    def visit_Char(self, node: Char, parents: Parents):
        return []

    def visit_And(self, node: And, parents: Parents):
        return []

    def visit_Not(self, node: Not, parents: Parents):
        return []


Vertex = TypeVar("Vertex", bound=Hashable)


def strongly_connected_components(
    graph: dict[Vertex, list[Vertex]], start: Vertex
) -> Iterator[tuple[Vertex, ...]]:
    """Find strongly connected components in a graph.

    Yields tuples of strongly connected components, where the first element
    is always the head of a chain.

    Args:
        graph: Directed graph.
        start: The start node.

    Returns:
        iterator
    """
    stack: OrderedDict[Vertex, int] = {}
    visited: set[Vertex] = set()

    def dfs(v):
        visited.add(v)
        if v in stack:
            beg = stack[v]
            yield tuple(stack.keys())[beg:]
            return
        stack[v] = len(stack)
        for u in graph[v]:
            yield from dfs(u)
        stack.popitem()

    for i in graph:
        if i not in visited:
            yield from dfs(i)


class AlternativeVisitor(Translator, GrammarPreVisitor):

    def translate(self, ctx: Context):
        return self.visit(ctx.grammar)

    def visit_Alt(self, node: Alt, parents: Parents):
        items = set()
        for i in node:
            items.add(self._visit(i, parents))
            if not i.nullable:
                return items
        return items

    def visit_NamedItem(self, node: NamedItem, parents: Parents):
        return self._visit(node.item, parents)

    def visit_ZeroOrOne(self, node: ZeroOrOne, parents: Parents):
        return self._visit(node.item, parents)

    def visit_ZeroOrMore(self, node: ZeroOrMore, parents: Parents):
        return self._visit(node.item, parents)

    def visit_OneOrMore(self, node: OneOrMore, parents: Parents):
        return self._visit(node.item, parents)

    def visit_Id(self, node: Id, parents: Parents):
        return node


class ComputeLR(Translator, GrammarPostVisitor):

    def translate(self, ctx: Context):
        NullableVisitor().translate(ctx)
        graph, rules = FirstGraphVisitor().translate(ctx)

        heads: list[Rule] = []

        for scc in strongly_connected_components(graph, ctx.grammar.entry.id):
            lr = LR([scc])

            logger.info("LR chain: %s", lr)

            head_rule = rules[lr.chains[0][0]]
            head_rule.head = True
            heads.append(head_rule)

            for involved in scc:
                rule = rules[involved]
                if rule.leftrec is None:
                    rule.leftrec = lr.copy()
                else:
                    rule.leftrec.chains.extend(lr.chains)

            alt_visitor = AlternativeVisitor()
            for head in heads:
                for alt in head.expr:
                    items = alt_visitor.visit(alt)
                    if not items:
                        continue
                    for n in head.leftrec.chains:
                        i = n[1] if len(n) > 1 else n[0]
                        if i in items:
                            alt.grower = True
