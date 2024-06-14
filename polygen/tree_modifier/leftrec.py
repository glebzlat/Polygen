from __future__ import annotations

from typing import Iterator, TypeVar, Hashable

from ..node import (
    GrammarVisitor,
    Grammar,
    Rule,
    Expr,
    Alt,
    NamedItem,
    Id,
    String,
    Char,
    AnyChar,
    Class,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    Not,
    And
)


class NullableVisitor(GrammarVisitor):
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.visited: set[str] = set()

    def visit_Grammar(self, node: Grammar):
        for r in node:
            self.visit(r)

    def visit_Rule(self, node: Rule) -> bool:
        if node.id in self.visited:
            return False
        self.visited.add(node.id)
        if self.visit(node.expr):
            node.nullable = True
        return node.nullable

    def visit_Expression(self, node: Expr) -> bool:
        for alt in node.alts:
            if self.visit(alt):
                return True
        return False

    def visit_Alt(self, node: Alt) -> bool:
        for item in node:
            if not self.visit(item):
                return False
        node.nullable = True
        return True

    def visit_NamedItem(self, node: NamedItem) -> bool:
        if self.visit(node.item):
            node.nullable = True
        return node.nullable

    def visit_Not(self, node: Not) -> bool:
        return True

    def visit_And(self, node: And) -> bool:
        return True

    def visit_ZeroOrOne(self, node: ZeroOrOne) -> bool:
        return True

    def visit_ZeroOrMore(self, node: ZeroOrMore) -> bool:
        return True

    def visit_OneOrMore(self, node: OneOrMore) -> bool:
        return False

    def visit_Repetition(self, node: Repetition) -> bool:
        return node.first == 0

    def visit_String(self, node: String) -> bool:
        return not node.chars

    def visit_Char(self, node: Char) -> bool:
        return False

    def visit_AnyChar(self, node: AnyChar) -> bool:
        return False

    def visit_Class(self, node: Class) -> bool:
        return not node.ranges


def compute_nullables(tree: Grammar):
    vis = NullableVisitor(tree)
    vis.visit(tree)


class FirstGraphVisitor(GrammarVisitor):
    def visit_Grammar(self, node: Grammar):
        graph = {}
        for r in node:
            key, val = self.visit(r)
            graph[key] = val
        return graph

    def visit_Rule(self, node: Rule):
        return node.id, self.visit(node.expr)

    def visit_Expr(self, node: Expr):
        names = set()
        for n in node:
            names |= self.visit(n)
        return names

    def visit_Alt(self, node: Alt):
        names = set()
        for i in node:
            assert type(i) is NamedItem
            names |= self.visit(i) or set()
            if not i.nullable:
                break
        return names

    def visit_NamedItem(self, node: NamedItem):
        return self.visit(node.item)

    def visit_Id(self, node: Id):
        return {node}

    def visit_String(self, node: String):
        return set()

    def visit_Char(self, node: Char):
        return set()

    def visit_And(self, node: And):
        return set()

    def visit_Not(self, node: Not):
        return set()


def make_first_graph(grammar: Grammar) -> dict[str, set[str]]:
    vis = FirstGraphVisitor()
    return vis.visit(grammar)


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
    stack: dict[str, int] = {}

    def dfs(v):
        if v in stack:
            beg = stack[v]
            yield tuple(stack.keys())[beg:]
            return
        stack[v] = len(stack)
        for u in graph[v]:
            yield from dfs(u)
        stack.popitem()

    yield from dfs(start)


def compute_lr(tree: Grammar):
    rules: dict[str, Rule] = {r.id: r for r in tree}

    compute_nullables(tree)
    graph = make_first_graph(tree)
    # print(graph)

    for scc in strongly_connected_components(graph, tree.entry.id):
        rules[scc[0]].head = True
        for involved in scc:
            rules[involved].leftrec = True
