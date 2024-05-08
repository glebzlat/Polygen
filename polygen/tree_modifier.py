import operator

from functools import reduce
from itertools import repeat
from typing import Iterable
from enum import StrEnum
from collections import defaultdict, Counter
from keyword import iskeyword

from .node import (
    Node,
    Grammar,
    Rule,
    Identifier,
    Expression,
    Alt,
    Part,
    Class,
    Range,
    And,
    Not,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    String,
    Char,
    AnyChar
)


class SemanticError(StrEnum):
    INVALID_RANGE = "invalid-range"
    INVALID_REPETITION = "invalid-rep"
    UNDEF_RULES = "undef-rules"
    REDEF_RULES = "redef-rules"
    REDEF_ENTRY = "redef-entry"
    ENTRY_NOT_DEFINED = "not-def-entry"


class SemanticWarning(StrEnum):
    UNUSED_RULES = "unused-rules"
    LOOKAHEAD_METANAME = "lookahead-metaname"
    METANAME_REDEF = "redef-metaname"


class TreeModifierError(Exception):
    def __init__(self, what: SemanticError, *nodes: Node):
        self.what = what
        self.nodes = nodes


class TreeModifierWarning(Warning):
    def __init__(self, what: SemanticWarning, *nodes: Node):
        self.what = what
        self.nodes = nodes


class ExpandClass:
    """Expand class of ranges into expression.

    ```
    Class(Range(m1, n1), ..., Range(mn, nn)) ->
        Expression(Alt(m1), ..., Alt(n1), ... Alt(mn), ..., Alt(nn))
    ```
    """

    def _expand_range(self, rng: Range) -> set[Char]:
        """Expand range.

        ```
        Range(m, n) -> {m, x1, x2, ..., n}
        ```
        """

        if rng.end is None:
            return {rng.beg}

        if rng.beg > rng.end:
            raise TreeModifierError(SemanticError.INVALID_RANGE, rng)
        return set(map(Char, range(rng.beg.code, rng.end.code + 1)))

    def visit_Class(self, node: Class):
        assert type(node.parent) is Part

        chars: set[Char] = reduce(
            operator.or_,
            (self._expand_range(rng) for rng in node),
            set())
        exp = Expression(*(Alt(Part(prime=c)) for c in sorted(chars)))
        node.parent.prime = exp

        return True


class ReplaceRep:
    """Replace repetition into a sequence of parts.

    ```
    Part(prime=E, quant=Repetition(n)) ->
        Expression(Alt(Part(prime=E1), ..., Part(prime=En)))
    Part(prime=E, quant=Repetition(n, m)) ->
        Expression(Alt(Part(prime=E1), ..., Part(prime=En), ..., Part(prime=Em))
    ```
    """

    def visit_Repetition(self, node: Repetition):
        assert type(node.parent) is Part

        if node.end and node.beg > node.end:
            raise TreeModifierError(SemanticError.INVALID_REPETITION, node)

        part: Part = node.parent
        prime = part.prime
        parts = [Part(prime=p) for p in repeat(prime, node.beg)]

        if not node.end:
            part.prime = Expression(Alt(*parts))
            part.quant = None
            return True

        opt_parts = [Part(prime=p)
                     for p in repeat(prime, node.end - node.beg)]
        parts.append(
            Part(prime=Expression(Alt(*opt_parts)),
                 quant=ZeroOrOne()))

        part.prime = Expression(Alt(*parts))
        part.quant = None

        return True


class ReplaceZeroOrOne:
    """Replace zero or one by an expression with an empty alternative

    ```
    Part(prime=E, quant=ZeroOrOne) ->
        Expression(Alt(Part(prime=E)), Alt())
    ```
    """

    def visit_ZeroOrOne(self, node: ZeroOrOne):
        assert type(node.parent) is Part

        part: Part = node.parent
        part.quant = None
        part.prime = Expression(
            Alt(
                Part(prime=part.prime)), Alt())

        return True


class ReplaceOneOrMore:
    """Replace one or more by a part, followed by zero or more parts

    ```
    Part(prime=E, quant=OneOrMore) ->
        Expression(Alt(
            Part(prime=E),
            Part(prime=E, quant=ZeroOrMore)))
    ```
    """

    def visit_OneOrMore(self, node: OneOrMore):
        assert type(node.parent) is Part

        part: Part = node.parent
        part.prime = Expression(
            Alt(
                Part(prime=part.prime),
                Part(prime=part.prime,
                     quant=ZeroOrMore())))
        part.quant = None

        return True


class EliminateAnd:
    """Replace AND(E) by NOT(NOT(E))

    ```
    Part(pred=Predicate.NOT, prime=E) ->
        Part(pred=Predicate.NOT, prime=Part(pred=Predicate.NOT, prime=E))
    ```
    """

    def visit_And(self, node: And):
        assert type(node.parent) is Part

        part: Part = node.parent
        nested = Expression(
            Alt(
                Part(pred=Not(), prime=part.prime)))
        part.prime = nested
        part.pred = Not()

        return True


class CheckUndefRedef:
    """Check for undefined rules in expressions and for rules with same names.

    If the rule is undefined (there is a rule identifier in expression, but
    there is no rule with such id), TreeModifierError with UNDEF_RULES error
    type will be raised. It will contain a sequence of `tuple[id, rule]`.

    If the rule is redefined, then the TreeModifierError with REDEF_RULES
    will be raised. It will contain all the duplicate rules.
    """

    def __init__(self):
        self.rhs_names = {}
        self.rule_names_set = set()

    def _get_parent_rule(self, node):
        while type(node) is not Rule:
            node = node.parent
        return node

    def visit_Identifier(self, node: Identifier):
        if type(node.parent) is Rule:
            if node in self.rule_names_set:
                return False
            self.rule_names_set.add(node)
        else:
            if node in self.rhs_names:
                return False
            self.rhs_names[node] = self._get_parent_rule(node)

        return False

    def visit_Grammar(self, node: Grammar):
        if diff := set(self.rhs_names) - self.rule_names_set:
            undef_rules = ((i, self.rhs_names[i]) for i in diff)
            raise TreeModifierError(SemanticError.UNDEF_RULES, *undef_rules)

        if len(node.nodes) > len(node.rules):
            counter = Counter(r.id for r in node.nodes)
            duplicates = (n for n, i in counter.most_common() if i > 1)
            dup_rules = (tuple(r for r in node.nodes if r.id == d)
                         for d in duplicates)
            raise TreeModifierError(SemanticError.REDEF_RULES, *dup_rules)


class SimplifyNestedExps:
    """Move nested expressions to their parent expressions in some cases.

    If an expression is occured inside the other expression, like so:

    ```
    Rule(A, Expression(Expression(e1, e2)))
    ```

    It is not needed to create an artificial rule for it:

    ```
    Rule(A, Expression(Ag))
    Rule(Ag, Expression(e1, e2))
    ```

    Instead, it is possible to move nested expression up to higher level:

    ```
    Rule(A, Expression(e1, e2))
    ```
    """

    def visit_Expression(self, node: Expression):
        if type(node.parent) is not Part:
            return False

        part: Part = node.parent
        if part.pred or part.quant:
            return False

        assert type(part.parent) is Alt
        alt = part.parent
        if len(alt) > 1:
            return False

        assert type(alt.parent) is Expression
        exp: Expression = alt.parent

        if len(exp) > 1:
            return False
        # if type(exp.parent) is not Rule:
        #     return False

        exp.alts.clear()
        exp.alts += node.alts
        for alt in node.alts:
            alt._parent = exp

        return True


class ReplaceNestedExps:
    """Creates new rules for nested expressions.

    Suppose the following grammar, containing nested expression `(En1 En2)`:

    ```
    A <- (En1 / En2) E1 E2
    ```

    Then it will be converted to

    ```
    A  <- Ag E1 E2
    Ag <- En1 / En2
    ```
    """

    # For nested expression in grammar:
    #   if expression already in created rules:
    #      id = created rule id with expression
    #   else:
    #      parent_id = get parent rule's id
    #      new_id = augment parent_id
    #      create rule with new_id and expression
    #      replace expression by new_id

    id_fmt = "{string}__GEN_{idx}"

    def __init__(self) -> None:
        self.created_rules: list[Rule] = []
        self.id_count: dict[Identifier, int] = {}

    def _get_rule_id(self, node: Node) -> Identifier:
        n = node
        while type(n) is not Rule:
            assert n.parent is not None
            n = n.parent
        return n.id

    def _create_id(self, id: Identifier) -> Identifier:
        idx = self.id_count.setdefault(id, 0) + 1
        self.id_count[id] = idx
        return Identifier(self.id_fmt.format(string=id.string, idx=idx))

    def visit_Expression(self, node: Expression):
        if type(node.parent) is Rule:
            return False

        assert type(node.parent) is Part
        part = node.parent

        for r in self.created_rules:
            if node == r.rhs:
                part.prime = r.name
                return True

        rule_id = self._get_rule_id(node)
        new_id = self._create_id(rule_id)
        new_rule = Rule(new_id, node)
        part.prime = new_id

        self.created_rules.append(new_rule)
        return True

    def visit_Grammar(self, node: Grammar):
        for rule in self.created_rules:
            result = node.add(rule)
            assert result
        added = len(self.created_rules)
        self.created_rules = []
        return bool(added)


class CreateAnyCharRule:
    """Create a rule to place AnyChar handling into one place.

    This is may be needed because of the formal definition of AnyChar.
    Formally, the '.' expression is a character class containing all
    of the terminals of the grammar. This artificial rule allows code
    generators to easily handle AnyChar logic in a custom manner.
    """

    def __init__(self):
        self.rule_id = Identifier("AnyChar__GEN")
        self.created_rule = Rule(
            self.rule_id.copy(),
            Expression(Alt(Part(prime=AnyChar())))
        )

    def visit_Grammar(self, node: Grammar):
        node.add(self.created_rule)
        return False

    def visit_AnyChar(self, node: AnyChar):
        assert node.parent is not None and type(node.parent) is Part
        part = node.parent

        assert part.parent is not None
        node1 = part.parent
        assert node1.parent is not None
        node2 = node1.parent
        assert node2.parent is not None
        node3 = node2.parent

        if type(node3) is Rule and node3.id == self.rule_id:
            # created rule
            return False

        part.prime = self.rule_id.copy()
        return False


class FindEntryRule:
    def __init__(self) -> None:
        self.entry: Rule | None = None

    def visit_Rule(self, node: Rule):
        if 'entry' in node.directives:
            if self.entry is not None:
                if self.entry == node:
                    return
                raise TreeModifierError(SemanticError.REDEF_ENTRY, node)
            self.entry = node

    def visit_Grammar(self, node: Grammar):
        if self.entry is None:
            raise TreeModifierError(SemanticError.ENTRY_NOT_DEFINED)
        node.entry = self.entry


class IgnoreRules:
    """Find rules with `@ignore` directive and add empty metanames.

    Rules with `@ignore` directive won't be captured by default.
    So the content that they match will not be passed to the semantic
    actions or returned.

    This will be useful e.g. for spacing rules -- spaces and comments
    don't matter.
    """

    def __init__(self):
        self.parts = defaultdict(list)

    def visit_Identifier(self, node: Identifier):
        part = node.parent
        self.parts[node].append(part)

    def visit_Rule(self, node: Rule):
        if 'ignore' in node.directives:
            for part in self.parts[node.id]:
                part.metaname = '_'


class GenerateMetanames:
    """Create metanames for all particles in the grammar tree.

    Particle with the Identifier will have the metaname, created from
    this Identifier's string. Particles with other kind of stuff will
    have indexed metanames: index, prepended with the underscore like
    this: `_1`.

    Lookahead particles must not have any metaname, except for the
    "ignore" metaname: `_`.

    Metanames that are given by the user would be preserved. If the
    user adds two (or more) metanames that are the same, so the second
    metaname will redefine the first, a warning will be raised.
    """

    def __init__(self):
        self.index = 1
        self.metanames = set()
        self.id_names = []

    def visit_Part(self, node: Part):
        metaname = node.metaname

        if type(node.pred) in (Not, And):
            if metaname is not None and metaname != '_':
                node.metaname = '_'
                raise TreeModifierWarning(SemanticWarning.LOOKAHEAD_METANAME)
            node.metaname = '_'
            return

        if type(node.prime) in (Char, String, AnyChar):
            varname = f'_{self.index}'
            self.index += 1
        elif type(node.prime) is Identifier:
            id = node.prime

            if metaname is not None:
                if metaname == '_':
                    return

                if metaname in self.metanames:
                    raise TreeModifierWarning(SemanticError.METANAME_REDEF)
                self.metanames.add(metaname)
                return

            if '__GEN' in id.string:
                varname = f'_{self.index}'
                self.index += 1
            else:
                varname = id.string.lower()
                if iskeyword(varname):
                    varname = '_' + varname
                if c := self.id_names.count(varname):
                    varname = f'{varname}{c}'
                self.id_names.append(varname)
        else:
            raise RuntimeError(f"unsupported node type: {node.prime}")

        node.metaname = varname

    def visit_Alt(self, node: Alt):
        self.index = 1
        self.metanames.clear()
        self.id_names.clear()


class DetectLeftRec:
    def visit_Rule(self, node: Rule):
        expr = node.expression
        if len(expr) == 0:
            return

        for alt in expr:
            if len(alt) and alt.parts[0].prime == node.id:
                node.leftrec = True


class TreeModifier:
    """Traverses the tree and modifies it.

    TreeModifier recursively traverses the tree in stages, applying the
    rewriting rules from each stage bottom-up (calls visitors post-order),
    until no rule was applied at least once.

    Stages are sequences of rules applied until no rule was applied.
    When all rules in the stage are done, then TreeModifier moves to the
    next stage. Stages are needed because of some rules require the tree
    being in some condition, created by another rules. So some rules should
    be run before another.
    """

    def __init__(self, stages: Iterable[Iterable[object]]):
        self.stages = stages
        self.errors: list[TreeModifierError] = []
        self.warnings: list[TreeModifierWarning] = []

    def _visit(self, node: Node, rules: list[object], flags: list[bool | None]):
        for child in node:
            self._visit(child, rules, flags)

        node_type_name = type(node).__name__
        method_name = f"visit_{node_type_name}"

        for i, rule in enumerate(rules):
            visit = getattr(rule, method_name, None)
            if not visit:
                continue

            try:
                flags[i] = visit(node) or flags[i]
            except TreeModifierError as exc:
                self.errors.append(exc)
                flags[i] = None
            except TreeModifierWarning as warn:
                self.warnings.append(warn)

    def visit(self, tree: Grammar):
        if not self.stages:
            return True, self.warnings, self.errors

        stage_done = False
        while not stage_done:
            for stage in self.stages:

                rules = list(stage)
                flags: list[bool | None] = [False for _ in rules]

                self._visit(tree, rules, flags)

                for i, rule in enumerate(rules):
                    if not flags[i]:
                        continue

                rules = [rule for i, rule in enumerate(rules) if flags[i]]
                stage_done = not rules

        success = not self.errors
        return success, self.warnings, self.errors
