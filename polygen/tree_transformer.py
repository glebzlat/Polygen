import operator

from functools import reduce
from itertools import repeat
from typing import Iterable

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
    Char,
    AnyChar
)

from .errors import (
    Errors,
    TreeTransformerError,
    TreeTransformerWarning,
)


class ExpandClassRule:
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
            raise TreeTransformerError(Errors.INVALID_RANGE, rng)
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


class ReplaceRepRule:
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
            raise TreeTransformerError(Errors.INVALID_REPETITION, node)

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


class ReplaceZeroOrOneRule:
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


class EliminateAndRule:
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


class CheckUndefRedefRule:
    """Check for undefined rules in expressions and for rules with same names.
    """

    def __init__(self):
        self.rhs_names_set = set()
        self.rule_names_set = set()
        self.rule_names = []

    def visit_Identifier(self, node: Identifier):
        if type(node.parent) is Rule:
            self.rule_names.append(node)
            if node in self.rule_names_set:
                return False
            self.rule_names_set.add(node)
        else:
            if node in self.rhs_names_set:
                return False
            self.rhs_names_set.add(node)

        return True

    def exit_Grammar(self, node: Grammar):
        if diff := self.rhs_names_set - self.rule_names_set:
            raise TreeTransformerError(Errors.UNDEF_RULES, *sorted(diff))

        if len(self.rule_names) > len(self.rule_names_set):
            names_count = {
                name: self.rule_names.count(name)
                for name in self.rule_names}
            duplicates = (
                name for name, count in names_count.items() if count > 1)
            raise TreeTransformerError(Errors.REDEF_RULES, *duplicates)


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


class ReplaceNestedExpsRule:
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

    def __init__(self):
        self.created_rules: list[Rule] = []
        self.id_count: dict[Identifier, int] = {}

    def _get_rule_id(self, node: Node) -> Identifier:
        n = node
        while type(n) is not Rule:
            n = n.parent
        return n.id

    def _create_id(self, id: Identifier) -> Identifier:
        idx = self.id_count.setdefault(id, 0) + 1
        self.id_count[id] = idx
        return Identifier(f"{id.string}_{idx}")

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
        self.rule_id = Identifier("AnyChar_generated")
        self.created_rule = Rule(
            self.rule_id.copy(),
            Expression(Alt(Part(prime=AnyChar())))
        )

    def visit_Grammar(self, node: Grammar):
        node.add(self.created_rule)
        return False

    def visit_AnyChar(self, node: AnyChar):
        part = node.parent

        node1 = part.parent
        node2 = node1.parent
        node3 = node2.parent
        if type(node3) is Rule and node3.id == self.rule_id:
            # created rule
            return False

        part.prime = self.rule_id.copy()
        return False


class TreeTransformer:
    def __init__(self, stages: Iterable[Iterable[object]]):
        self.stages = stages
        self.errors: list[TreeTransformerError] = []
        self.warnings: list[TreeTransformerWarning] = []

    def _visit(self, node: Node, rules: list[object], flags: list[bool]):
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
            except TreeTransformerError as exc:
                self.errors.append(exc)
                flags[i] = None
            except TreeTransformerWarning as warn:
                self.warnings.append(warn)

    def transform(self, tree: Grammar):
        if not self.stages:
            return True, self.warnings, self.errors

        stage_done = False
        while not stage_done:
            for stage in self.stages:

                rules = list(stage)
                flags = [False for _ in rules]

                self._visit(tree, rules, flags)

                for i, rule in enumerate(rules):
                    if not flags[i]:
                        continue

                rules = [rule for i, rule in enumerate(rules) if flags[i]]
                stage_done = not rules

        success = not self.errors
        return success, self.warnings, self.errors

    def traverse(self, tree: Grammar):
        return self.transform(tree)
