from contextlib import contextmanager

from .node import (
    Grammar,
    Rule,
    Identifier,
    AnyChar,
    Char,
    String,
    Not,
    And,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore
)


class GeneratorError(Exception):
    pass


class PythonGenerator:
    def __init__(self, stream=None):
        self.indentation = ''
        self.stream = stream

    def put(self, *args, newline=True, indent=True):
        if indent:
            print(end=self.indentation, file=self.stream)
        print(*args, end='', file=self.stream)
        if newline:
            print(file=self.stream)

    @contextmanager
    def indent(self, level: int = 1):
        save = self.indentation
        try:
            self.indentation += '    ' * level
            yield
        finally:
            self.indentation = save

    def generate(self, grammar: Grammar):
        for i, rule in enumerate(grammar):
            self.gen_rule(i, rule)

    def gen_rule(self, rule_index: int, rule: Rule):
        if rule_index != 0:
            self.put(indent=False)

        self.put('@memoize')
        self.put(f'def _{rule.name.string}(self):')

        with self.indent():
            self.put('pos = self._mark()')
            for i, alt in enumerate(rule.rhs):
                self.gen_alt(alt, rule, i)
            self.put('return None')

    def gen_alt(self, alt, rule, alt_index):
        items = []
        put_newline = len(alt) > 1

        self.put('if (', newline=put_newline)
        with self.indent():
            for i, part in enumerate(alt):
                self.gen_part(part, items, alt_index, i, put_newline)
        self.put('):', indent=put_newline)

        with self.indent():
            self.put('return True')
        self.put('self._reset(pos)')

    def gen_part(self, part, items, alt_index, part_index, newline):
        if type(part.prime) is Char:
            fn, args = 'self._expectc', (part.prime,)
        elif type(part.prime) is Identifier:
            fn, args = f'self._{part.prime.string}', ()
        elif type(part.prime) is String:
            fn, args = 'self._expects', (part.prime,)
        elif type(part.prime) is AnyChar:
            fn, args = 'self._expectc', ()
        else:
            raise GeneratorError('unsupported node type', part)

        if type(part.quant) is ZeroOrOne:
            fn, args = 'self._maybe', (fn, *args)
        elif type(part.quant) is ZeroOrMore:
            fn, args = 'self._loop', (False, fn, *args)
        elif type(part.quant) is OneOrMore:
            fn, args = 'self._loop', (True, fn, *args)

        if type(part.pred) is Not:
            fn, args = 'self._lookahead', (False, fn, *args)
        elif type(part.pred) is And:
            fn, args = 'self._lookahead', (True, fn, *args)

        args = ', '.join(str(i) for i in args)
        call = f'{fn}({args})'
        cond = 'is not None' if part.pred is None else ''
        op = 'and' if part_index else ''

        string = ' '.join(filter(None, (op, call, cond)))
        self.put(string, newline=newline, indent=newline)
