from __future__ import annotations

from collections import defaultdict, Counter
from keyword import iskeyword

from ..node import (
    islookahead,
    DLL,
    Grammar,
    Rule,
    MetaRef,
    MetaRule,
    Expr,
    Alt,
    NamedItem,
    Id,
    Char,
    AnyChar,
    Class,
    Range,
    Repetition,
    And,
    Not
)

from .errors import (
    UndefRulesError,
    RedefRulesError,
    UndefMetaRulesError,
    RedefMetaRulesError,
    UndefEntryError,
    RedefEntryError,
    LookaheadMetanameWarning,
    MetanameRedefError,
    UnusedMetaRuleWarning,
    InvalidRangesError,
    InvalidRepetitionsError,
    GatheredSemanticErrors
)


class CheckUndefinedRules:
    """Finds rules, that are referenced but not found in the grammar."""

    def __init__(self):
        self.named_items: defaultdict[list[Id]] = defaultdict(list)
        self.rule_names: set[Id] = set()
        self.done = False

    def visit_Rule(self, node: Rule, parents):
        self.rule_names.add(node.id)

    def visit_Id(self, node: Id, parents):
        if type(parents[-1]) in (MetaRef, MetaRule):
            return
        self.named_items[node].append(node)

    def apply(self):
        items = self.named_items
        if diff := set(items) - self.rule_names:
            undef_rules = {i: items[i] for i in diff}
            raise UndefRulesError(undef_rules)
        self.done = True


class CheckRedefinedRules:
    """Finds rules that are defined more than once."""

    def __init__(self):
        self.rules = defaultdict(list)
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
            raise RedefRulesError(redef)
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

    def __init__(self):
        self.created_exprs: dict[Expr, Id] = {}
        self.id_count: Counter[Id] = Counter()
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

    def __init__(self):
        self.entry: Rule | None = None
        self.done = False

    def visit_Grammar(self, node: Grammar, parents):
        if self.entry is None:
            raise UndefEntryError(None)
        node.entry = self.entry

    def visit_Rule(self, node: Rule, parents):
        if not node.entry:
            return

        if self.entry is not None:
            raise RedefEntryError([self.entry, node])
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

    def __init__(self, strict=False):
        self.strict = strict
        self.chars: set[Char] = set()
        self.rule_id = Id("AnyChar__GEN")
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

    def __init__(self):
        self.items: defaultdict[str, list[NamedItem]] = defaultdict(list)
        self.done = False

    def visit_NamedItem(self, node: NamedItem, parents):
        if isinstance(node.inner_item, Id):
            self.items[node.inner_item.value].append(node)

    def visit_Rule(self, node: Rule, parents):
        if node.ignore:
            for i in self.items[node.id.value]:
                if i.name is None:
                    i.name = Id(NamedItem.IGNORE)

    def apply(self):
        self.done = True


class GenerateMetanames:
    """Generates metanames which will be used by semantic actions."""

    def __init__(self):
        self.index = 1
        self.metanames = set()
        self.id_names = Counter()
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
                print(self.metanames)
                raise MetanameRedefError(node)
            self.metanames.add(metaname)
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
                if iskeyword(metaname):
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
            raise MetanameRedefError(node)
        node.name = Id(metaname)
        self.metanames.add(metaname)

    def visit_Alt(self, node: Alt, parents):
        self.index = 1
        self.metanames.clear()
        self.id_names.clear()

    def apply(self):
        self.done = True


class AssignMetaRules:
    """Finds metarules and assigns them to alts that references to them."""

    def __init__(self):

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
            alts = self.refs.pop(node.id)
            self.assigned.add(node.id)
            for alt in alts:
                alt.metarule = node

    def _check_redefined(self):
        duplicates = {id: rules for id, rules in self.metarules.items()
                      if len(rules) > 1}
        if duplicates:
            raise RedefMetaRulesError(duplicates)

    def visit_Grammar(self, node: Grammar, parents):
        if self.stage == 1:
            node.metarules = None

    def apply(self):
        if self.stage == 0:
            self.stage = 1
        elif self.stage == 1:
            if self.refs:
                raise UndefMetaRulesError(dict(self.refs))
            self._check_redefined()
            self.done = True


class ValidateNodes:
    def __init__(self):
        self.ranges: list[Range] = []
        self.reps: list[Repetition] = []
        self.done = False

    def visit_Range(self, node: Range, parents):
        if node.last and node.last < node.first:
            self.ranges.append(node)

    def visit_Repetition(self, node: Repetition, parents):
        if node.last is not None and node.last < node.first:
            self.reps.append(node)

    def apply(self):
        rng_exc = InvalidRangesError(self.ranges) if self.ranges else None
        rep_exc = InvalidRepetitionsError(self.reps) if self.reps else None

        if rng_exc or rep_exc:
            raise GatheredSemanticErrors([rng_exc, rep_exc])

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
