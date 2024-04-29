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
)

from .errors import (
    Errors,
    TreeTransformerError,
    TreeTransformerWarning,
)


class SemanticRule:
    node_type: type | Iterable[type]

    def apply(self, node: Node) -> bool:
        return False

    def finalize(self) -> None:
        pass


class ExpandClassRule(SemanticRule):
    """Expand class of ranges into expression.

    ```
    Class(Range(m1, n1), ..., Range(mn, nn)) ->
        Expression(Alt(m1), ..., Alt(n1), ... Alt(mn), ..., Alt(nn))
    ```
    """

    node_type = Class

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

    def apply(self, node: Class):
        assert type(node.parent) is Part

        chars: set[Char] = reduce(
            operator.or_,
            (self._expand_range(rng) for rng in node),
            set())
        exp = Expression(*(Alt(Part(prime=c)) for c in sorted(chars)))
        node.parent.prime = exp

        return True


class ReplaceRepRule(SemanticRule):
    """Replace repetition into a sequence of parts.

    ```
    Part(prime=E, quant=Repetition(n)) ->
        Expression(Alt(Part(prime=E1), ..., Part(prime=En)))
    Part(prime=E, quant=Repetition(n, m)) ->
        Expression(Alt(Part(prime=E1), ..., Part(prime=En), ..., Part(prime=Em))
    ```
    """

    node_type = Repetition

    def apply(self, node: Repetition):
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


class ReplaceZeroOrOneRule(SemanticRule):
    """Replace zero or one by an expression with an empty alternative

    ```
    Part(prime=E, quant=ZeroOrOne) ->
        Expression(Alt(Part(prime=E)), Alt())
    ```
    """

    node_type = ZeroOrOne

    def apply(self, node: ZeroOrOne):
        assert type(node.parent) is Part

        part: Part = node.parent
        part.quant = None
        part.prime = Expression(
            Alt(
                Part(prime=part.prime)), Alt())

        return True


class ReplaceOneOrMore(SemanticRule):
    """Replace one or more by a part, followed by zero or more parts

    ```
    Part(prime=E, quant=OneOrMore) ->
        Expression(Alt(
            Part(prime=E),
            Part(prime=E, quant=ZeroOrMore)))
    ```
    """

    node_type = OneOrMore

    def apply(self, node: OneOrMore):
        assert type(node.parent) is Part

        part: Part = node.parent
        # print(part)
        # print(part.parent)
        part.prime = Expression(
            Alt(
                Part(prime=part.prime),
                Part(prime=part.prime,
                     quant=ZeroOrMore())))
        part.quant = None
        # print(part.parent)

        return True


class EliminateAndRule(SemanticRule):
    """Replace AND(E) by NOT(NOT(E))

    ```
    Part(pred=Predicate.NOT, prime=E) ->
        Part(pred=Predicate.NOT, prime=Part(pred=Predicate.NOT, prime=E))
    ```
    """

    node_type = And

    def apply(self, node: And):
        assert type(node.parent) is Part

        part: Part = node.parent
        nested = Expression(
            Alt(
                Part(pred=Not(), prime=part.prime)))
        part.prime = nested
        part.pred = Not()

        return True


class CheckUndefRedefRule(SemanticRule):
    """Check for undefined rules in expressions and for rules with same names.
    """

    node_type = Identifier

    def __init__(self):
        self.rhs_names_set = set()
        self.rule_names_set = set()
        self.rule_names = []

    def apply(self, node: Identifier):
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

    def finalize(self):
        if diff := self.rhs_names_set - self.rule_names_set:
            raise TreeTransformerError(Errors.UNDEF_RULES, *sorted(diff))

        if len(self.rule_names) > len(self.rule_names_set):
            names_count = {
                name: self.rule_names.count(name)
                for name in self.rule_names}
            duplicates = (
                name for name, count in names_count.items() if count > 1)
            raise TreeTransformerError(Errors.REDEF_RULES, *duplicates)


class SimplifyNestedExps(SemanticRule):
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

    node_type = Expression

    def apply(self, node: Node):
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

        del exp.alts[0]
        exp.alts += node.alts
        for alt in node.alts:
            alt._parent = exp

        return True


class ReplaceNestedExpsRule(SemanticRule):
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

    node_type = (Grammar, Expression)

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
        self.grammar: Grammar | None = None

    def _get_rule_id(self, node: Node) -> Identifier:
        n = node
        while type(n) is not Rule:
            n = n.parent
        return n.id

    def _create_id(self, id: Identifier) -> Identifier:
        idx = self.id_count.setdefault(id, 0) + 1
        self.id_count[id] = idx
        return Identifier(f"{id.string}_{idx}")

    def apply(self, node):
        nodetype = type(node)

        if nodetype is Grammar:
            if self.grammar is None:
                self.grammar = node
            return False

        elif nodetype is Expression:
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
        return False

    def finalize(self):
        assert len(self.created_rules)
        for rule in self.created_rules:
            result = self.grammar.add(rule)
            assert result
        self.created_rules = []


class TreeTransformer:
    def __init__(self, stages: list[list[SemanticRule]]):
        self.stages = stages
        self.errors: list[TreeTransformerError] = []
        self.warnings: list[TreeTransformerWarning] = []

    def _traverse(self, node: Node, rules):
        rule_infos = rules.get(type(node))
        if rule_infos:
            for rule_info in rule_infos:
                if rule_info[1] is None:
                    continue

                rule, flag = rule_info
                try:
                    rule_info[1] = rule.apply(node) or flag
                except TreeTransformerError as exc:
                    self.errors.append(exc)
                    rule_info[1] = None
                except TreeTransformerWarning as warn:
                    self.warnings.append(warn)

        for child in node:
            self._traverse(child, rules)

    def traverse(self, tree: Grammar):
        for stage in self.stages:

            rules: dict[type, SemanticRule] = {}
            for rule in stage:
                nodes = []
                if isinstance(rule.node_type, type):
                    nodes.append(rule.node_type)
                else:
                    nodes += rule.node_type

                # append a list[rule, flag]
                # flag may be True, if rule is applied at least once,
                # False if not, and None if rule raised an exception
                for node in nodes:
                    actions = rules.setdefault(node, [])
                    actions.append([rule, False])

            stage_done = False
            while not stage_done:
                self._traverse(tree, rules)

                # remove rules that aren't applied at least once
                # or rules that raised an exception. If no rule is applied,
                # then move to the next stage
                for node_type in tuple(rules.keys()):
                    rule_list = rules[node_type]
                    applied_rules = []

                    for rule_info in rule_list:
                        rule, flag = rule_info
                        if not flag:
                            continue
                        try:
                            rule.finalize()
                            rule_info[1] = False
                            applied_rules.append(rule_info)
                        except TreeTransformerError as exc:
                            self.errors.append(exc)
                            rule_info[1] = None
                        except TreeTransformerWarning as warn:
                            self.warnings.append(warn)

                    if not applied_rules:
                        rules.pop(node_type)
                    else:
                        rules[node_type] = applied_rules

                stage_done = not rules

        success = not self.errors
        return success, self.warnings, self.errors
