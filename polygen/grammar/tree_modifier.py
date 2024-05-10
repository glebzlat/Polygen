import operator

from functools import reduce
from itertools import repeat
from typing import Iterable
from collections import defaultdict, Counter
from keyword import iskeyword

from .node import (
    Node,
    Grammar,
    Rule,
    MetaRef,
    MetaRule,
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


class SemanticError(Exception):
    """Base class for semantic errors raised by tree modifiers.

    `SemanticError` instances normally should not be raised to the end user,
    but collected by the `TreeModifier`. If at least one `SemanticError`
    occured, `TreeModifier` will raise `TreeModifierError`.

    SemanticError must define severity level:
        low: Exception registered. Modifier, that has raised this exception,
            is not discarded.
        moderate: Exception registered and the modifier that raised it is
            discarded.
        critical: Exception halts traversal process and causes TreeModifier
            to raise TreeModifierError immediately.

    `SemanticError` instances may contain node (or nodes) that caused
    the error, but does not give any text representation. This is the
    formatter's responsibility.
    """

    severity = "critical"


class InvalidRangeError(SemanticError):
    """Malformed range quantifier.

    Raised when the upper bound of a range is less than the lower bound:
    `end < beg`.
    """

    severity = "low"

    def __init__(self, node: Range):
        self.node = node


class InvalidRepetitionError(SemanticError):
    """Malformed repetition particle.

    Raised when the upper bound of a repetition is less than the lower bound:
    `end < beg`.
    """

    severity = "low"

    def __init__(self, node: Repetition):
        self.node = node


class UndefRulesError(SemanticError):
    """Undefined rules error.

    Raised, when an identifier in the right-hand side of a rule not found
    in rule names set.

    Args:
        rules: A mapping from undefined identifier to the rule, where
            it was found.
    """

    severity = "low"

    def __init__(self, rules: dict[Identifier, Rule]):
        self.rules = rules


class RedefRulesError(SemanticError):
    """Raised when the rule with the same id is defined more than once.

    Args:
        rules: A dictionary that maps an identifier to a sequence
            of rules with this identifier.
    """

    severity = "low"

    def __init__(self, rules: dict[Identifier, list[Rule]]):
        self.rules = rules


class RedefEntryError(SemanticError):
    """Raised when one than one entry point is defined."""

    severity = "moderate"


class EntryNotDefinedError(SemanticError):
    """Raised when no entry point defined."""

    severity = "moderate"


class MetanameRedefError(SemanticError):
    """Raised when metaname is redefined.

    Redefinition of the metaname will probably lead to compiler/interpreter
    errors (redefined variable) or at least to malfunctioning parser.
    """

    severity = "low"


class UndefMetaRefsError(SemanticError):
    """Undefined metarules error.

    Raised when a metarule reference's id not found in metarules set.

    Args:
        alts: A mapping from undefined identifier to the alternative, where
            it was found.
    """

    def __init__(self, rules: dict[Identifier, Alt]):
        self.rules = rules

    severity = "moderate"


class RedefMetaRulesError(SemanticError):
    """Raised when the metarule with the same id is defined more than once.

    Args:
        rules: A dictionary that maps an identifier to a sequence
            of rules with this identifier.
    """

    severity = "moderate"

    def __init__(self, rules: dict[Identifier, MetaRule]):
        self.rules = rules


class SemanticWarning(Warning):
    """Base class for semantic warnings raised by tree modifiers.

    If at least one semantic warning was raised during the tree traversal
    process, it will be collected and cause the `TreeModifier` to raise
    `TreeModifierWarning`.

    `SemanticWarning` instances may contain node (or nodes) that caused
    the error, but does not give any text representation. This is the
    formatter's responsibility.
    """

    pass


class UnusedRulesWarning(SemanticWarning):
    pass


class LookaheadMetanameWarning(SemanticWarning):
    """Raised when a metaname is assigned to a lookahead particle.

    Lookahead particles does not consume any input string, so their value
    is not so useful in the semantic actions.
    """


class UnusedMetaRuleWarning(SemanticWarning):
    pass


class TreeModifierError(Exception):
    """Exception that signals one or more semantic errors during tree traversal.

    This exception is a container for underlying `SemanticError`-bases
    instances. Raised exceptions are accessible through the standard
    exception's `args` attribute.

    If at least one `SemanticError` was raised, parser generation process
    should be halted, as continuation will cause errors in the later stages
    or will lead to non-working parser. If the semantic error is raised,
    the tree is probably is in the incorrect state.
    """

    pass


class TreeModifierWarning(Warning):
    """Warning that signals one or more semantic warnings during traversal.

    This warning is a container for underlying `SemanticWarning`-bases
    instances. Raised warnings are accessible through the standard warnings's
    `args` attribute.

    Semantic warnins signals that there are mistakes in the grammar, which
    may lead to malfunctioning parser, but it is possible to continue the
    generation process.
    """

    pass


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
            raise InvalidRangeError(rng)
        return set(map(Char, range(rng.beg.code, rng.end.code + 1)))

    def visit_Class(self, node: Class, parents):
        assert type(parents[-1]) is Part

        chars: set[Char] = reduce(
            operator.or_,
            (self._expand_range(rng) for rng in node),
            set())
        exp = Expression(*(Alt(Part(prime=c)) for c in sorted(chars)))
        parents[-1].prime = exp

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

    def visit_Repetition(self, node: Repetition, parents):
        assert type(parents[-1]) is Part

        if node.end and node.beg > node.end:
            raise InvalidRepetitionError(node)

        part: Part = parents[-1]
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

    def visit_ZeroOrOne(self, node: ZeroOrOne, parents):
        assert type(parents[-1]) is Part

        part: Part = parents[-1]
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

    def visit_OneOrMore(self, node: OneOrMore, parents):
        assert type(parents[-1]) is Part

        part: Part = parents[-1]
        part.prime = Expression(
            Alt(
                Part(prime=part.prime),
                Part(prime=part.prime,
                     quant=ZeroOrMore())))
        part.quant = None

        return True


# class EliminateAnd:
#     """Replace AND(E) by NOT(NOT(E))
#
#     ```
#     Part(pred=Predicate.NOT, prime=E) ->
#         Part(pred=Predicate.NOT, prime=Part(pred=Predicate.NOT, prime=E))
#     ```
#     """
#
#     def visit_And(self, node: And, parents):
#         assert type(parents[-1]) is Part
#
#         part: Part = parents[-1]
#         nested = Expression(
#             Alt(
#                 Part(pred=Not(), prime=part.prime)))
#         part.prime = nested
#         part.lookahead = Not()
#
#         return True


class CheckUndefRedef:
    """Check for undefined rules in expressions and for rules with same names.
    """

    def __init__(self):
        self.rhs_names = {}
        self.rule_names_set = set()

    def _get_parent_rule(self, parents):
        idx = -2
        while type(parents[idx]) is not Rule:
            idx -= 1
        return parents[idx]

    def visit_Identifier(self, node: Identifier, parents):
        if type(parents[-1]) is Rule:
            if node in self.rule_names_set:
                return False
            self.rule_names_set.add(node)
        elif type(parents[-1]) in (MetaRule, MetaRef):
            return False
        else:
            if node in self.rhs_names:
                return False
            self.rhs_names[node] = self._get_parent_rule(parents)

        return False

    def visit_Grammar(self, node: Grammar, parents):
        if diff := set(self.rhs_names) - self.rule_names_set:
            undef_rules = {i: self.rhs_names[i] for i in diff}
            raise UndefRulesError(undef_rules)

        counter = Counter(r.id for r in node.nodes)
        assert all(r is not None for r in counter)
        duplicates = (n for n, i in counter.most_common() if i > 1)
        dup_rules = {d: [r for r in node.nodes if r.id == d]
                     for d in duplicates}
        if dup_rules:
            raise RedefRulesError(dup_rules)

        return None


# class SimplifyNestedExps:
#     """Move nested expressions to their parent expressions in some cases.
#
#     If an expression is occured inside the other expression, like so:
#
#     ```
#     Rule(A, Expression(Expression(e1, e2)))
#     ```
#
#     It is not needed to create an artificial rule for it:
#
#     ```
#     Rule(A, Expression(Ag))
#     Rule(Ag, Expression(e1, e2))
#     ```
#
#     Instead, it is possible to move nested expression up to higher level:
#
#     ```
#     Rule(A, Expression(e1, e2))
#     ```
#     """
#
#     def visit_Expression(self, node: Expression, parents):
#         if type(parents[-1]) is not Part:
#             return False
#
#         part: Part = parents[-1]
#         if part.lookahead or part.quant:
#             return False
#
#         assert type(part.parent) is Alt
#         alt = part.parent
#         if len(alt) > 1:
#             return False
#
#         assert type(alt.parent) is Expression
#         exp: Expression = alt.parent
#
#         if len(exp) > 1:
#             return False
#
#         exp.alts.clear()
#         exp.alts += node.alts
#         for alt in node.alts:
#             alt._parent = exp
#
#         return True


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

    id_fmt = "{string}__GEN_{idx}"

    def __init__(self) -> None:
        self.created_rules: list[Rule] = []
        self.id_count: dict[Identifier, int] = {}

    def _get_rule_id(self, parents) -> Identifier:
        idx = -2
        while type(parents[idx]) is not Rule:
            idx -= 1
        return parents[idx].id

    def _create_id(self, id: Identifier) -> Identifier:
        idx = self.id_count.setdefault(id, 0) + 1
        self.id_count[id] = idx
        return Identifier(self.id_fmt.format(string=id.string, idx=idx))

    def visit_Expression(self, node: Expression, parents):

        # For nested expression in grammar:
        #   if expression already in created rules:
        #      replace expression by an id of the created rule
        #   else:
        #      parent_id = get parent rule's id
        #      new_id = augment parent_id
        #      create rule with new_id and expression
        #      replace expression by new_id

        if type(parents[-1]) is Rule:
            return False

        assert type(parents[-1]) is Part
        part = parents[-1]

        for r in self.created_rules:
            if node == r.expr:
                part.prime = r.id
                return True

        rule_id = self._get_rule_id(parents)
        new_id = self._create_id(rule_id)
        new_rule = Rule(new_id, node)
        part.prime = new_id

        self.created_rules.append(new_rule)
        return True

    def visit_Grammar(self, node: Grammar, parents):
        for rule in self.created_rules:
            result = node.add(rule)
            assert result
        self.created_rules.clear()
        return None


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

    def visit_Grammar(self, node: Grammar, parents):
        node.add(self.created_rule)
        return False

    def visit_AnyChar(self, node: AnyChar, parents):
        assert parents[-1] is not None and type(parents[-1]) is Part
        part = parents[-1]

        # if it is a newly created rule
        parent = parents[-4]
        if type(parent) is Rule and parent.id == self.rule_id:
            return False

        part.prime = self.rule_id.copy()
        return False


class FindEntryRule:
    def __init__(self) -> None:
        self.entry: Rule | None = None

    def visit_Rule(self, node: Rule, parents):
        if 'entry' in node.directives:
            if self.entry is not None:
                if self.entry == node:
                    return
                raise RedefEntryError(node)
            self.entry = node
        return False

    def visit_Grammar(self, node: Grammar, parents):
        if self.entry is None:
            raise EntryNotDefinedError()
        node.entry = self.entry
        return None


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

    def visit_Identifier(self, node: Identifier, parents):
        part = parents[-1]
        self.parts[node].append(part)
        return False

    def visit_Rule(self, node: Rule, parents):
        if 'ignore' in node.directives:
            for part in self.parts[node.id]:
                part.metaname = '_'
        return False


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
        self.id_names = Counter()

    def visit_Part(self, node: Part, parents):
        metaname = node.metaname

        if type(node.lookahead) in (Not, And):
            if metaname is not None and metaname != '_':
                copy = node.copy()
                node.metaname = '_'
                raise LookaheadMetanameWarning(copy)
            node.metaname = '_'
            return False

        if metaname is not None:
            if metaname == '_':
                return False

            if metaname in self.metanames:
                raise MetanameRedefError(node)
            return False

        if type(node.prime) in (Char, String, AnyChar):
            metaname = f'_{self.index}'
            self.index += 1

        elif type(node.prime) is Identifier:
            id = node.prime

            if '__GEN' in id.string:
                metaname = f'_{self.index}'
                self.index += 1

            else:
                metaname = id.string.lower()
                if iskeyword(metaname):
                    metaname = '_' + metaname

                idx = self.id_names[metaname]
                self.id_names[metaname] += 1
                if idx:
                    metaname = f'{metaname}{idx}'

        else:
            raise RuntimeError(f"unsupported node type: {node.prime}")

        if metaname in self.metanames:
            raise MetanameRedefError(node)
        node.metaname = metaname
        self.metanames.add(metaname)
        return False

    def visit_Alt(self, node: Alt, parents):
        self.index = 1
        self.metanames.clear()
        self.id_names.clear()
        return False


class SubstituteMetaRefs:
    """Finds and subsitutes MetaRefs by MetaRules.
    """

    def __init__(self):
        self.refs = defaultdict(list)
        self.metarules = defaultdict(list)
        self.stage = 0

    def visit_MetaRef(self, node: MetaRef, parents):
        if self.stage == 0:
            self.refs[node.id].append(parents[-1])
        return True

    def visit_MetaRule(self, node: MetaRule, parents):
        if self.stage == 1:
            if type(parents[-1]) is Alt:
                return False
            self.metarules[node.id].append(node)
            alts = self.refs.pop(node.id, None)
            if alts is None:
                raise UnusedMetaRuleWarning(node)
            alt: Alt
            for alt in alts:
                alt.metarule = node.copy()
        return True

    def _check_redefined(self):
        duplicates = {id: rules for id, rules in self.metarules.items()
                      if len(rules) > 1}
        if len(duplicates):
            raise RedefMetaRulesError(duplicates)

    def visit_Grammar(self, node: Grammar, parents):
        if self.stage == 0:
            self.stage = 1
            return True
        if self.stage == 1:
            self.stage = 2
            if self.refs:
                raise UndefMetaRefsError(dict(self.refs))
            self._check_redefined()
            node.remove_metarules()
            return False


# class DetectLeftRec:
#     def visit_Rule(self, node: Rule, parents):
#         expr = node.expression
#         if len(expr) == 0:
#             return
#
#         for alt in expr:
#             if len(alt) and alt.parts[0].prime == node.id:
#                 node.leftrec = True


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

    If the modifier raises an exception with the severity greater than 'low',
    then it will be discarded for the rest of the traversal process.

    Modifier's `visit_*` methods should return True, if the modifier wants
    to be called in the next tree traversal, False, if not and None if modifier
    wants to be discarded without an error in the current traversal.
    """

    def __init__(self, stages: Iterable[Iterable[object]]):
        self.stages = stages
        self.errors: list[SemanticError] = []
        self.warnings: list[SemanticWarning] = []

    def _visit(self,
               node: Node,
               nodes: list[Node],
               rules: list[object],
               flags: list[bool | None]):
        nodes.append(node)
        for child in node:
            self._visit(child, nodes, rules, flags)

        node_type_name = type(node).__name__
        method_name = f"visit_{node_type_name}"

        nodes.pop()
        for i, rule in enumerate(rules):
            if flags[i] is None:
                continue

            visit = getattr(rule, method_name, None)
            if not visit:
                continue

            try:
                flags[i] = visit(node, nodes)

            except SemanticError as exc:
                self.errors.append(exc)

                if exc.severity == "critical":
                    raise TreeModifierError(self.errors)
                elif exc.severity == "moderate":
                    flags[i] = None
                elif exc.severity == "low":
                    pass
                else:
                    raise RuntimeError(
                        f"invalid severity value {exc.severity!r}")

            except SemanticWarning as warn:
                self.warnings.append(warn)

    def visit(self, tree: Grammar):
        if not self.stages:
            return

        stages_flags: tuple[list[bool | None], ...]
        stages_flags = tuple([True for _ in s] for s in self.stages)
        done_stages = [False for _ in self.stages]

        max_iterations = sum(len(s) for s in self.stages) * 2

        for _ in range(max_iterations):
            for i, (stage, flags) in enumerate(zip(self.stages, stages_flags)):
                rules = [rule for i, rule in enumerate(stage) if flags[i]]
                if not rules:
                    done_stages[i] = True

                for i in range(len(flags)):
                    if flags[i] is not None:
                        flags[i] = False

                nodes = []
                self._visit(tree, nodes, rules, flags)

                for i, rule in enumerate(rules):
                    if not flags[i]:
                        continue

            if all(done_stages):
                break

        else:
            msg = "max iterations count exceeded"
            stages_flags_dump = [list(zip(s, f)) for s, f
                                 in zip(self.stages, stages_flags)]
            raise RuntimeError(msg, stages_flags_dump)

        if self.errors:
            raise TreeModifierError(*self.errors)

        if self.warnings:
            raise TreeModifierWarning(*self.warnings)
