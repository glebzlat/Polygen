from io import TextIOBase

from polygen.utility import reindent

from polygen.gen_base import GeneratorBase
from polygen.node import GrammarVisitor

from polygen.node import (
    DLL,
    Grammar,
    Rule,
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
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    And,
    Not
)


class Generator(GeneratorBase, GrammarVisitor):
    def __init__(self, grammar: Grammar, stream: TextIOBase, config):
        self.grammar = grammar
        self.config = config
        super().__init__(stream)

    def generate(self):
        self.visit(self.grammar)

    def visit_Grammar(self, node: Grammar):
        for i, r in enumerate(self.grammar):
            self.visit(r, i)

    def visit_Rule(self, node: Rule, index: int):
        if index:
            # Place empty line between rules, but not before the first rule
            self.emptyline()

        if node.leftrec is not None:
            if node.head:
                self.put("@_memoize_lr")
        else:
            self.put("@_memoize")

        self.put(f"def _{node.id.value}(self):")

        with self.indent():
            if node.nullable:
                self.put("# Nullable")
            if node.leftrec is not None:
                self.put("# Left recursive:")
                for line in str(node.leftrec).split('\n'):
                    self.put(f"#   {line}")

            self.put("_begin_pos = self._mark()")
            self.visit(node.expr)
            self.put("return None")

    def visit_Expr(self, node: Expr):
        for i, alt in enumerate(node):
            self.visit(alt, i)

    def visit_Alt(self, node: Alt, index: int):
        variables = []

        length = DLL.length(node.items)
        if length == 0:
            self.put("if True:")

        elif length == 1:
            self.put("if (", newline=False)
            self.visit(node.items, 0, variables, newline=False)
            self.put("):", indent=False)

        else:
            self.put("if (")
            with self.indent():
                for i, item in enumerate(node):
                    self.visit(item, i, variables, newline=True)
            self.put("):")

        with self.indent():

            if node.nullable:
                self.put("# Nullable")

            self.put(f"# {str(node).replace('\n', ' ')}")

            # Unpack values from Success wrappers
            for var in variables:
                self.put(f"{var} = {var}.value")

            if node.metarule:
                self.emptyline()

                assert type(node.metarule) is MetaRule
                self.put(f"# Metarule: {node.metarule.id.value}")
                expr = reindent(node.metarule.expr, level=self._indent_level)
                self.put(expr.strip('\n'), indent=0)
            else:
                if len(variables) == 1:
                    self.put(f"return Success({variables[0]})")
                elif variables:
                    # Remove empty successes
                    return_value = ', '.join(variables)
                    self.put(f"__tup = tuple(x for x in ({return_value}) "
                             f"if x is not None)")
                    self.put("return Success(__tup)")
                else:
                    self.put("return Success()")

        self.put("self._reset(_begin_pos)")

    def visit_NamedItem(self,
                        node: NamedItem,
                        index: int,
                        variables: list[str],
                        newline: bool):

        self.put("and " if index else "", newline=False, indent=newline)

        ignore = node.name == Id(NamedItem.IGNORE)
        assign = "" if ignore else f"{node.name} := "
        parts = self.visit(node.item)

        fn, *args = parts
        body = ', '.join(str(i) for i in args)
        call = f"{assign}{fn}({body})"

        if not ignore:
            call = f"({call})"

        self.put(call, indent=False, newline=False)

        if newline:
            self.put("", indent=False)

        if not ignore:
            variables.append(node.name.value)

    def visit_ZeroOrOne(self, node: ZeroOrOne):
        return "self._maybe", *self.visit(node.item)

    def visit_ZeroOrMore(self, node: ZeroOrMore):
        return "self._loop", "False", *self.visit(node.item)

    def visit_OneOrMore(self, node: OneOrMore):
        return "self._loop", "True", *self.visit(node.item)

    def visit_Repetition(self, node: Repetition):
        return "self._rep", node.first, node.last, *self.visit(node.item)

    def visit_And(self, node: And):
        return "self._lookahead", "True", *self.visit(node.item)

    def visit_Not(self, node: Not):
        return "self._lookahead", "False", *self.visit(node.item)

    def visit_String(self, node: String):
        return "self._expects", node

    def visit_Char(self, node: Char):
        return "self._expectc", node

    def visit_AnyChar(self, node: AnyChar):
        return ("self._expectc",)

    def visit_Id(self, node: Id):
        return (f"self._{node.value}",)

    def visit_Class(self, node: Class):
        return "self._ranges", *(self.visit(r) for r in node)

    def visit_Range(self, node: Range) -> str:
        last = node.last or node.first
        return f"({node.first}, {last})"
