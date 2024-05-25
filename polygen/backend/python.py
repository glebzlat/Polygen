from io import TextIOBase

from ..generator.util import reindent

from ..generator.parser_generator import ParserGenerator
from ..grammar.visitor import GrammarVisitor

from ..grammar.node import (
    Grammar,
    Rule,
    Alt,
    Part,
    Identifier,
    AnyChar,
    Char,
    String,
    Class,
    Not,
    And,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition
)


class Generator(ParserGenerator, GrammarVisitor):
    def __init__(self, grammar: Grammar, stream: TextIOBase):
        self._grammar = grammar
        super().__init__(stream)

    def generate(self):
        for i, r in enumerate(self._grammar):
            self.visit(r, i)

    def visit_Rule(self, node: Rule, index: int):
        if index:
            # Place empty line between rules, but not before the first rule
            self._emptyline()

        self._put('@_memoize_lr' if node.leftrec else '@_memoize')
        self._put(f'def _{node.id.string}(self):')

        with self._indent():
            self._put('_begin_pos = self._mark()')

            for i, alt in enumerate(node.expr):
                self.visit(alt, i)

            self._put('return None')

    def visit_Alt(self, node: Alt, index: int):
        variables = []

        length = len(node.parts)
        if length == 0:
            self._put('if True:')

        elif length == 1:
            self._put('if (', newline=False)
            self.visit(node.parts[0], 0, variables, newline=False)
            self._put('):', indent=False)

        else:
            self._put('if (')
            with self._indent():
                for i, part in enumerate(node.parts):
                    self.visit(part, i, variables, newline=True)
            self._put('):')

        with self._indent():
            if node.metarule:
                self._put(f'# {node.metarule.id.string}')
                self._put(
                    reindent(node.metarule.expr, level=self._indent_level),
                    indent=0)
            else:
                retval = ', '.join(variables)
                self._put(f'return {retval}' if retval else 'return True')
        self._put('self._reset(_begin_pos)')

    def visit_Part(self,
                   node: Part,
                   index: int,
                   variables: list[str],
                   newline: bool):
        parts = []

        cond = 'is not None'
        if node.lookahead is not None:
            parts += self.visit(node.lookahead)
            cond = None

        if node.quant is not None:
            parts += self.visit(node.quant)

        parts += self.visit(node.prime)

        var = None
        if node.metaname != '_':
            var = node.metaname
            variables.append(var)

        fn, args = parts[0], ', '.join(str(i) for i in parts[1:])
        op = 'and' if index else ''
        call = f'{fn}({args})'
        assignment = f'({var} := {call})' if var else call

        string = ' '.join(filter(None, (op, assignment, cond)))
        self._put(string, newline=newline, indent=newline)

    def visit_Not(self, node: Not):
        return 'self._lookahead', False

    def visit_And(self, node: And):
        return 'self._lookahead', True

    def visit_ZeroOrOne(self, node: ZeroOrOne):
        return ['self._maybe']

    def visit_ZeroOrMore(self, node: ZeroOrMore):
        return 'self._loop', False

    def visit_OneOrMore(self, node: OneOrMore):
        return 'self._loop', True

    def visit_Repetition(self, node: Repetition):
        return 'self._rep', node.beg, node.end

    def visit_Char(self, node: Char):
        return 'self._expectc', str(node)

    def visit_Identifier(self, node: Identifier):
        return [f'self._{node.string}']

    def visit_String(self, node: String):
        return 'self._expects', str(node)

    def visit_AnyChar(self, node: AnyChar):
        return ['self._expectc']

    def visit_Class(self, node: Class):
        pairs = ((r.beg, r.end) for r in node)
        char_pairs = ((b, e if e is not None else b) for b, e in pairs)
        str_pairs = tuple((chr(b.code), chr(e.code)) for b, e in char_pairs)

        return 'self._ranges', *str_pairs
