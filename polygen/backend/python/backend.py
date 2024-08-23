from io import StringIO
from typing import Any, Optional
from pathlib import Path

from polygen.__version__ import __version__
from polygen.utility import reindent

from polygen.generator.base import CodeGeneratorBase
from polygen.generator.runner import RunnerBase, Executable
from polygen.generator.config import Option

from polygen.node import (
    DLL,
    Grammar,
    LR,
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


POLYGEN_IMPORTS = """
from polygen.node import (
    ParseInfo,
    Grammar,
    Directive,
    Include,
    Entry,
    ToplevelQuery,
    BackendQuery,
    Ignore,
    Include,
    Rule,
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
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    And,
    Not
)
"""


class CodeGenerator(CodeGeneratorBase):

    NAME = "python"
    LANGUAGE = "Python"
    VERSION = "0.0.1"
    FILES = ["parser.py.in"]
    OPTIONS = {
        "polygen_imports": Option(bool, default=False)
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate(self,
                 grammar: Grammar,
                 options: dict[str, Any]) -> dict[str, str | StringIO]:

        # with self.directive("imports"):
        #     if options["polygen_imports"]:
        #         self.put(POLYGEN_IMPORTS, newline=False)

        with self.directive("grow_rules"):
            pass

        with self.directive("entry"):
            self.put(grammar.entry.id.value, newline=False)

        with self.directive("body"):
            self.visit(grammar)
        return self._directives

    def visit_Grammar(self, node: Grammar):
        for i, r in enumerate(node):
            self.visit(r, i)

    def visit_Rule(self, node: Rule, index: int):
        if index:
            # Place empty line between rules, but not before the first rule
            self.emptyline()

        if node.leftrec:
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

            if not node.head:
                self.put("_begin_pos = self._mark()")
            self.visit(node.expr, node)
            self.put("return None")

        lr_alts = f"_lr_alts_{node.id}"
        if lr_alts in self._directives:
            self.emptyline()
            self.put(self._directives[lr_alts].getvalue(), newline=False,
                     line_ending=False)
            del self._directives[lr_alts]

    def visit_Expr(self, node: Expr, rule: Rule):
        if rule.head:
            alts, seeds, growers = [], [], []
            for i, alt in enumerate(node, 1):
                name = f"_{rule.id}_Alt_{i}"
                alts.append(name)
                self.put(f"if (alt := self.{alts[-1]}()) is not None:")
                with self.indent():
                    self.put("return alt")

                if alt.grower:
                    growers.append(name)
                else:
                    seeds.append(name)

            with self.directive("grow_rules"):
                seeds_str = ', '.join(f"self.{i}" for i in seeds)
                growers_str = ', '.join(f"self.{i}" for i in growers)
                self.put(f'"_{rule.id}": ([{seeds_str}], [{growers_str}]),')

            with self.directive(f"_lr_alts_{rule.id}"):
                for i, alt in enumerate(node):
                    self.put(f"def {alts[i]}(self):")
                    with self.indent():
                        self.put("_begin_pos = self._mark()")
                        self.visit(alt, i)
                    if alt.right is not None:
                        self.emptyline()
        else:
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

            if node.items is not None:
                items = ' '.join(str(i.item) for i in node.items.forward())
                self.put(f"# {items}")

            if node.metarule:
                self.emptyline()

                assert type(node.metarule) is MetaRule
                self.put(f"# Metarule: {node.metarule.id.value}")
                expr = reindent(node.metarule.expr, level=self._indent_level)
                self.put(expr.strip('\n'), indent=0)
            else:
                if len(variables) == 1:
                    self.put(f"return {variables[0]}")
                else:
                    items = ', '.join(variables)
                    self.put(f"return [{items}]")

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

        call = f"{call} is not None"

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


class Runner(RunnerBase):

    DEPENDENCIES = ["python3"]

    def run(self, file: Path) -> tuple[int, str]:
        python = self["python3"]
        exitcode, output = python.run(self.parser_file, file,
                                      capture_output=True, timeout=5)
        return exitcode, output

    def setup(self):
        self.parser_file = self.parser_files["parser.py.in"]

    def setdown(self):
        pass
