from __future__ import annotations

import logging

from collections import defaultdict, Counter
from typing import Iterator, TypeVar, Hashable, OrderedDict, Optional

from .node import (
    GrammarVisitor,
    islookahead,
    DLL,
    Grammar,
    Rule,
    LR,
    MetaRef,
    MetaRule,
    Expr,
    Alt,
    NamedItem,
    Id,
    String,
    Char,
    AnyChar,
    Class,
    Range,
    Repetition,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    And,
    Not
)

from .utility import reindent

logger = logging.getLogger("polygen.modifier")


class Options:
    reserved_words: set[str]

    def __init__(self, **kwargs):
        for attr, val in kwargs.items():
            setattr(self, attr, val)


class TreeModifierWarning(Warning):
    """Gathers multiple semantic warnings."""

    def __str__(self):
        return '\n'.join(str(a) for a in self.args)


class Context:
    def __init__(self):
        self._stack = []

        self.grammar: Optional[Grammar] = None
        self.rule: Optional[Rule] = None
        self.alt: Optional[Alt] = None
        self.named_item: Optional[NamedItem] = None

    def __getitem__(self, idx):
        return self._stack[idx]

    def __len__(self) -> int:
        return len(self._stack)

    def append(self, item):
        self._add_node(item)
        self._stack.append(item)

    def pop(self, idx=-1):
        item = self._stack.pop(idx)
        self._remove_node(type(item))
        return item

    def _add_node(self, node):
        if isinstance(node, Grammar):
            self.grammar = node
        elif isinstance(node, Rule):
            self.rule = node
        elif isinstance(node, Alt):
            self.alt = node
        elif isinstance(node, NamedItem):
            self.named_item = node

    def _remove_node(self, type):
        if isinstance(self.grammar, type):
            self.grammar = None
        elif isinstance(self.rule, type):
            self.rule = None
        elif isinstance(self.alt, type):
            self.alt = None
        elif isinstance(self.named_item, type):
            self.named_item = None


class ModifierVisitor:
    def __init__(self, modifiers):
        self.modifiers = modifiers
        self.warnings = []

    def apply(self, tree: Grammar):
        for m in self.modifiers:
            while not m.done:
                self._visit(tree, Context(), m)
                m.apply()

        if self.warnings:
            raise TreeModifierWarning(*self.warnings)

    def _visit(self, node, parents, modifier):
        if modifier.done:
            return
        parents.append(node)
        for child in node:
            self._visit(child, parents, modifier)
        parents.pop()
        self._visit_post(node, parents, modifier)

    def _visit_post(self, node, parents, modifier):
        node_type_name = type(node).__name__
        method_name = f"visit_{node_type_name}"
        visitor = getattr(modifier, method_name, None)
        if visitor is not None:
            try:
                visitor(node, parents)

            except SemanticWarning as warn:
                self.warnings.append(warn)


class SemanticWarning(Warning):
    pass


class LookaheadMetanameWarning(SemanticWarning):
    """Raised by GenerateMetanames if lookahead node has metaname.

    Contains one And / Not node.
    """

    def __str__(self):
        lines = ["Lookahead metanames are not allowed:"]
        assert len(self.args) == 1
        node = self.args[0]
        if node.parse_info:
            lines.append(f"  at {node.parse_info}:")
        lines.append(f"{reindent(str(self.args[0]), 1)}")
        return '\n'.join(lines)


class UnusedMetaRuleWarning(SemanticWarning):
    """Metarule was defined but not applied to any rule's alternative.

    Contains one MetaRule node.
    """

    def __str__(self):
        lines = ["Unused metarule:"]
        assert len(self.args) == 1
        node = self.args[0]
        if node.parse_info:
            lines.append(f"  at {node.parse_info}:")
        lines.append(reindent(str(self.args[0]), 1))
        return '\n'.join(lines)


class SemanticError(Exception):
    """Base class for exceptions raised by modifiers."""


class UndefEntryError(SemanticError):
    """Entry rule not defined."""

    def __str__(self):
        return "Entry is not defined"


class RedefEntryError(SemanticError):
    """There are more than one rule with '@entry' directive.

    Contains two Rule nodes: first defined entry and redefined entry.
    """

    def __str__(self):
        lines = ["Redefined entry rules:"]
        first, second = self.args
        lines.append("first defined here:")
        if first.parse_info:
            lines.append(f"  {first.parse_info}")
        lines.append(reindent(str(first), 1))
        lines.append("second defined here:")
        if second.parse_info:
            lines.append(f"  {second.parse_info}")
        lines.append(reindent(str(second), 1))
        return '\n'.join(lines)


class UndefRulesError(SemanticError):
    """Rule mentioned in an expression but not found in the grammar."""

    def __str__(self):
        lines = []
        for id, rules in self.args:
            lines.append(f"Undefined rule {id}:")
            for i, r in enumerate(rules, 1):
                # XXX: parse_info start pointer is displaced
                lines.append(reindent(str(r), 1))
                if id.parse_info:
                    pos = id.parse_info.start
                    length = id.parse_info.end - pos - 1
                    lines.append(' ' * pos + '^' + '~' * length)
                if i != len(rules):
                    lines.append('\n')
        return '\n'.join(lines)


class RedefRulesError(SemanticError):
    """Rule defined more than once."""

    def __str__(self):
        lines = []
        for id, rules in self.args:
            lines.append("Redefined rule {id}:")
            if id.parse_info:
                lines.append(f"First defined here: {id.parse_info}")
            for i, r in enumerate(rules, 1):
                if r.id.parse_info:
                    lines.append(f"  at {r.id.parse_info}:")
                lines.append(reindent(str(r), 1))
                if i != len(rules):
                    lines.append('\n')
        return '\n'.join(lines)


class UndefMetaRulesError(SemanticError):
    """Metarule mentioned in an expression but not found in the grammar."""

    def __str__(self):
        lines = []
        for id, alts in self.args:
            lines.append(f"Undefined metarule {id}:")
            for i, alt in enumerate(alts, 1):
                lines.append(reindent(str(alt), 1))
                # XXX: Parse info start position is displaced.
                # if there are multiple alternatives,
                # then start position of all alternatives will be the same
                # why?
                if info := alt.metarule.name.parse_info:
                    pos = info.start - 1
                    length = info.end - info.start
                    lines.append(' ' * pos + '^' + '~' * length)
                    lines.append(f"at {info}")
                if i != len(alts):
                    lines.append('')
        return '\n'.join(lines)


class RedefMetaRulesError(SemanticError):
    """Metarule defined more than once."""

    def __str__(self):
        lines = []
        for id, rules in self.args:
            lines.append("Redefined metarule {id}:")
            for i, r in enumerate(rules, 1):
                if info := r.id.parse_info:
                    lines.append(f"at {info}")
                lines.append(reindent(str(r), 1))
                if i != len(rules):
                    lines.append('')
        return '\n'.join(lines)


class MetanameRedefError(SemanticError):
    """Multiple nodes in one alternative has the same metaname.

    Redefinition of the metaname will probably lead to compiler/interpreter
    errors (redefined variable) or at least to malfunctioning parser.

    Contains two nodes with the same metaname.
    """

    def __str__(self):
        first, second = self.args
        lines = [f"Redefined metaname {first.name}"]
        lines.append(reindent(str(first), 1))
        if info := first.name.parse_info:
            lines.append(f"at {info}")
        lines.append(reindent(str(second), 1))
        if info := first.name.parse_info:
            lines.append(f"at {info}")
        return '\n'.join(lines)


class RangeRepError(SemanticError):
    """Invalid repetition and range nodes.

    Contains two lists: a list of ranges and a list of repetitions. Range and
    repetition nodes have `beg` and `end` boundaries. If `end` is greater
    than `beg`, node considered invalid.
    """

    # TODO: add __str__ method


class CheckUndefinedRules:
    """Finds rules, that are referenced but not found in the grammar."""

    def __init__(self, options: Options):
        self.named_items: defaultdict[list[Rule]] = defaultdict(list)
        self.rule_names: set[Id] = set()
        self.options = options
        self.done = False

    def visit_Rule(self, node: Rule, parents):
        self.rule_names.add(node.id)

    def visit_Id(self, node: Id, parents: Context):
        if type(parents[-1]) in (MetaRef, MetaRule):
            return
        self.named_items[node].append(parents.rule)

    def apply(self):
        items = self.named_items
        if diff := set(items) - self.rule_names:
            raise UndefRulesError(*((i, items[i]) for i in diff))
        self.done = True


class CheckRedefinedRules:
    """Finds rules that are defined more than once."""

    def __init__(self, options: Options):
        self.rules = defaultdict(list)
        self.options = options
        self.done = False

    def visit_Rule(self, node: Rule, parents):
        self.rules[node.id].append(node)

    def apply(self):
        redef = {}
        for id, rules in self.rules.items():
            if len(rules) == 1:
                continue
            redef[id] = rules

        if redef:
            raise RedefRulesError(*redef.items())
        self.done = True


class ReplaceNestedExprs:
    """Creates artificial rules for subexpressions.

    Translates this grammar:

    ```
    A <- (En1 / En2) E1
    ```

    To this:

    ```
    A  <- Ag E1
    Ag <- En1 / En2
    ```
    """

    def __init__(self, options: Options):
        self.created_exprs: dict[Expr, Id] = {}
        self.id_count: Counter[Id] = Counter()
        self.options = options
        self.done = False

    def _get_rule_id(self, parents) -> Id | None:
        for p in reversed(parents):
            if type(p) is Rule:
                return p.id
        return None

    def _create_id(self, id: Id) -> Id:
        self.id_count[id] = idx = self.id_count[id] + 1
        return Id(f"{id}__GEN_{idx}")

    def visit_Expr(self, node: Expr, parents):
        if type(parents[-1]) is Rule:
            return

        # Replace expression by the reference
        if node in self.created_exprs:
            parents[-1].item = self.created_exprs[node]
            return

        rule_id = self._get_rule_id(parents)
        assert rule_id is not None

        new_id = self._create_id(rule_id)
        parents[-1].item = new_id

        self.created_exprs[node] = new_id

    def visit_Grammar(self, node: Grammar, parents):
        rules = (Rule(id, expr) for expr, id in self.created_exprs.items())
        lst = Rule.from_iterable(rules)
        if lst:
            node.rules.end.emplace_after(lst)

    def apply(self):
        self.done = True


class FindEntryRule:
    """Tries to find the rule marked as `@entry`."""

    def __init__(self, options: Options):
        self.entry: Rule | None = None
        self.options = options
        self.done = False

    def visit_Grammar(self, node: Grammar, parents):
        if self.entry is None:
            raise UndefEntryError
        node.entry = self.entry

    def visit_Rule(self, node: Rule, parents):
        if not node.entry:
            return

        if self.entry is not None:
            raise RedefEntryError(self.entry, node)
        self.entry = node

    def apply(self):
        self.done = True


class CreateAnyChar:
    """Create artificial rule for AnyChar node.

    If the `strict` argument is True, then collects all characters that are
    appeared in the grammar and forms character class from them. This
    corresponds to the formal definition (Bryan Ford, Parsing Expression
    Grammars):

    > We consider the '.' expression in the concrete syntax to be a character
    > class containing all of the terminals in [the set of terminal symbols].
    """

    def __init__(self, options: Options, strict=False):
        self.strict = strict
        self.chars: set[Char] = set()
        self.rule_id = Id("AnyChar__GEN")
        self.options = options
        self.done = False

    def visit_Char(self, node: Char, parents):
        self.chars.add(node)

    def visit_AnyChar(self, node: AnyChar, parents):
        assert parents[-1] is not None
        if self.strict:
            parents[-1].item = self.rule_id

    def visit_Grammar(self, node: Grammar, parents):
        if self.strict:
            cls = charset_to_class(self.chars)

            logger.info("AnyChar class: %s", cls)

            rule = Rule(self.rule_id, Expr([Alt([NamedItem(None, cls)])]))
            if DLL.length(node.rules):
                node.rules.end.insert_after(rule)

    def apply(self):
        self.done = True


class IgnoreRules:
    """Finds rules marked with `@ignore` and marks all its references.

    Backend should use marked NamedItems -- items, that marked with
    `NamedItem.IGNORE` value should not return any values.
    """

    def __init__(self, options: Options):
        self.ids: set[Id] = set()
        self.items: defaultdict[Id, list[NamedItem]] = defaultdict(list)
        self.options = options
        self.done = False

    def visit_NamedItem(self, node: NamedItem, parents):
        inner = node.inner_item
        if isinstance(inner, Id):
            self.items[inner].append(node)

    def visit_Rule(self, node: Rule, parents):
        if node.ignore:
            self.ids.add(node.id)

    def apply(self):
        for rule_id in self.ids:
            for i in self.items[rule_id]:
                if i.name is None:
                    i.name = Id(NamedItem.IGNORE)
        self.done = True


class GenerateMetanames:
    """Generates metanames which will be used by semantic actions."""

    def __init__(self, options: Options):
        self.index = 1
        self.metanames = {}
        self.id_names = Counter()
        self.options = options
        self.reserved_words = options.reserved_words
        self.done = False

    def visit_NamedItem(self, node: NamedItem, parents):
        if node.name is not None:
            metaname = node.name.value
        else:
            metaname = None

        # It is forbidden for lookahead items to have metanames, because
        # lookahead returns nothing meaningful
        if islookahead(node.item):
            if metaname is not None and metaname != NamedItem.IGNORE:
                metaname = NamedItem.IGNORE
                raise LookaheadMetanameWarning(node)

        if metaname is not None:
            if metaname == NamedItem.IGNORE:
                return

            # Names assigned by the user must be original
            if metaname in self.metanames:
                raise MetanameRedefError(self.metanames[metaname], node)
            self.metanames[metaname] = node
            return

        if type(node.item) in (And, Not):
            metaname = NamedItem.IGNORE

        # Nonterminal or subexpression
        elif isinstance(node.inner_item, Id):
            name = node.inner_item.value

            if "__GEN" in name:
                # Ignore artificial metanames (generated from subexpressions)
                metaname = f"_{self.index}"
                self.index += 1

            else:
                # Create metaname from nonterminal name
                metaname = node.inner_item.value.lower()
                if metaname in self.reserved_words:
                    metaname = f"_{metaname}"

                # Prepend metaname with index, if it is already appeared
                idx = self.id_names[metaname]
                self.id_names[metaname] += 1
                if idx:
                    metaname = f"{metaname}{idx}"

        # Terminal
        else:
            metaname = f"_{self.index}"
            self.index += 1

        if metaname in self.metanames:
            raise MetanameRedefError(self.metanames[metaname], node)
        node.name = Id(metaname)
        self.metanames[metaname] = node

    def visit_Alt(self, node: Alt, parents):
        self.index = 1
        self.metanames.clear()
        self.id_names.clear()

    def apply(self):
        self.done = True


class AssignMetaRules:
    """Finds metarules and assigns them to alts that references to them."""

    def __init__(self, options: Options):

        # Alts that hold references to the metarule
        self.refs: defaultdict[Id, list[Alt]] = defaultdict(list)

        # Ids of metarules that are already assigned to alts
        self.assigned: set[Id] = set()

        # Needed to find rules with the same id
        self.metarules: defaultdict[Id, list[MetaRule]] = defaultdict(list)

        # Modifier works in 2 stages:
        #   1: Collects references
        #   2: Searches metarules and assigns them to alts
        self.stage = 0
        self.options = options
        self.done = False

    def visit_Alt(self, node: Alt, parents):
        if self.stage == 0:
            if type(node.metarule) is MetaRef:
                self.refs[node.metarule.name].append(node)

    def visit_MetaRule(self, node: MetaRule, parents):
        if self.stage == 1:
            if type(parents[-1]) is Alt:
                return

            self.metarules[node.id].append(node)

            # Assigned set is needed to prevent falsy warnings in case
            # when the metarule was assigned and another metarule with
            # the same id was found.
            if node.id not in self.refs and node.id not in self.assigned:
                raise UnusedMetaRuleWarning(node)
            if node.id not in self.refs:
                return
            alts = self.refs.pop(node.id)
            self.assigned.add(node.id)
            for alt in alts:
                alt.metarule = node

    def _check_redefined(self):
        duplicates = {id: rules for id, rules in self.metarules.items()
                      if len(rules) > 1}
        if duplicates:
            raise RedefMetaRulesError(*duplicates.items())

    def visit_Grammar(self, node: Grammar, parents):
        if self.stage == 1:
            node.metarules = None

    def apply(self):
        if self.stage == 0:
            self.stage = 1
        elif self.stage == 1:
            if self.refs:
                raise UndefMetaRulesError(*self.refs.items())
            self._check_redefined()
            self.done = True


class ValidateRangesAndReps:
    def __init__(self, options: Options):
        self.ranges: list[Range] = []
        self.reps: list[Repetition] = []
        self.options = options
        self.done = False

    def visit_Range(self, node: Range, parents):
        if node.last and node.last < node.first:
            self.ranges.append(node)

    def visit_Repetition(self, node: Repetition, parents):
        if node.last is not None and node.last < node.first:
            self.reps.append(node)

    def apply(self):
        if self.ranges or self.reps:
            raise RangeRepError(self.ranges, self.reps)

        self.done = True


def charset_to_class(chars: set[Char]) -> Class:
    """Create class of ranges from the set of characters."""
    ranges = []
    lst = []
    for c in sorted(chars):
        if not lst or c.code - lst[-1].code == 1:
            lst.append(c)
        else:
            if len(lst) == 1:
                beg, end = lst[0], None
            else:
                beg, end = lst[0], lst[-1]
            ranges.append(Range(beg, end))
            lst.clear()

    if lst:
        if len(lst) == 1:
            beg, end = lst[0], None
        else:
            beg, end = lst[0], lst[-1]
        ranges.append(Range(beg, end))

    return Class(ranges)


class NullableVisitor(GrammarVisitor):
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.visited: set[Id] = set()
        self.nullables: set[Id] = set()

    def visit_Grammar(self, node: Grammar):
        for r in node:
            self.visit(r)

        self.visited.clear()
        for r in node:
            self.visit(r)

    def visit_Rule(self, node: Rule) -> bool:
        if node.id in self.visited:
            return False
        self.visited.add(node.id)
        if self.visit(node.expr):
            node.nullable = True
            self.nullables.add(node.id)
        return node.nullable

    def visit_Expr(self, node: Expr) -> bool:
        for alt in node:
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

    def visit_Id(self, node: Id) -> bool:
        return node in self.nullables

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
        graph: dict[Id, list[Id]] = {}
        rules: dict[Id, Rule] = {}
        for r in node:
            if isinstance(r, MetaRule):
                continue
            key, val = self.visit(r)
            graph[key] = val
            rules[key] = r
        return graph, rules

    def visit_Rule(self, node: Rule):
        return node.id, self.visit(node.expr)

    def visit_Expr(self, node: Expr):
        names, added = [], set()
        for n in node:
            for n in self.visit(n):
                if n in added:
                    continue
                names.append(n)
                added.add(n)
        return names

    def visit_Alt(self, node: Alt):
        names, added = [], set()
        for i in node:
            assert type(i) is NamedItem
            for n in (self.visit(i) or []):
                if n in added:
                    continue
                names.append(n)
                added.add(n)
            if not i.nullable:
                break
        return names

    def visit_NamedItem(self, node: NamedItem):
        return self.visit(node.item)

    def visit_ZeroOrOne(self, node: ZeroOrOne):
        return self.visit(node.item)

    def visit_ZeroOrMore(self, node: ZeroOrMore):
        return self.visit(node.item)

    def visit_OneOrMore(self, node: OneOrMore):
        return self.visit(node.item)

    def visit_Id(self, node: Id):
        return [node]

    def visit_String(self, node: String):
        return []

    def visit_Char(self, node: Char):
        return []

    def visit_And(self, node: And):
        return []

    def visit_Not(self, node: Not):
        return []


def make_first_graph(grammar: Grammar) -> dict[str, list[str]]:
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


class AlternativeVisitor(GrammarVisitor):
    def visit_Alt(self, node: Alt):
        items = set()
        for i in node:
            items.add(self.visit(i))
            if not i.nullable:
                return items
        return items

    def visit_NamedItem(self, node: NamedItem):
        return self.visit(node.item)

    def visit_ZeroOrOne(self, node: ZeroOrOne):
        return self.visit(node.item)

    def visit_ZeroOrMore(self, node: ZeroOrMore):
        return self.visit(node.item)

    def visit_OneOrMore(self, node: OneOrMore):
        return self.visit(node.item)

    def visit_Id(self, node: Id):
        return node


class ComputeLR:

    # Improved left recusion: https://github.com/glebzlat/packrat-improved-lr

    def __init__(self, options: Options):
        self.options = options
        self.done = False

    def visit_Grammar(self, node: Grammar, parents):
        compute_nullables(node)
        graph, rules = make_first_graph(node)

        if logger.isEnabledFor(logging.INFO):
            lines = []
            for k, v in graph.items():
                if not v:
                    continue
                strs = ', '.join(str(i) for i in v)
                lines.append(f"  {k}: [{strs}]")
            logger.info("first graph:\n%s", '\n'.join(lines))

        heads: list[Rule] = []
        # breakpoint()
        for scc in strongly_connected_components(graph, node.entry.id):
            lr = LR([scc])

            logger.info("lr chain: %s", lr)

            head_rule = rules[lr.chains[0][0]]
            head_rule.head = True
            heads.append(head_rule)

            for involved in scc:
                rule = rules[involved]
                if rule.leftrec is None:
                    rule.leftrec = lr.copy()
                else:
                    rule.leftrec.chains.extend(lr.chains)

        # This algorithm has extremely bad time complexion:
        # compute nullables,
        # make first graph,
        # compute and iterate SCCs,
        # find growers
        # results in roughly O(n^5)
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

        self.done = True

    def apply(self):
        self.done = True
