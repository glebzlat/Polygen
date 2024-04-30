from contextlib import contextmanager

from .node import (
    Grammar,
    Rule,
    Identifier,
    Alt,
    AnyChar,
    Char,
    String,
    Not,
    ZeroOrMore
)


class GeneratorError(Exception):
    pass


class Generator:
    def __init__(self, stream=None):
        self.indentation = ''
        self.stream = stream

    def put(self, *args):
        print(end=self.indentation, file=self.stream)
        print(*args, file=self.stream)

    def putni(self, *args):
        "Put no indent - print without indenting"
        print(*args, file=self.stream)

    @contextmanager
    def indent(self):
        save = self.indentation
        try:
            self.indentation += '    '
            yield
        finally:
            self.indentation = save

    def join(self, *parts: str):
        return '\n'.join(self.indentation + s for s in parts)

    def generate(self, grammar: Grammar):
        for rule in grammar:
            self.gen_rule(rule)

    def gen_rule(self, rule: Rule):
        self.putni()
        self.put('@memoize')
        self.put(f'def _{rule.name.string}(self):')

        with self.indent():
            self.put('pos = self._mark()')

            empty_alt = False
            for alt in rule.rhs:
                empty_alt = self.gen_alt(alt)

            if not empty_alt:
                self.put('self._reset(pos)')
                self.put('return False')

    def gen_alt(self, alt: Alt):
        self.gen_part(alt.parts, 0, len(alt.parts))
        return len(alt) == 0

    def gen_part(self, parts, index, length, not_pred=False):
        last = index == len(parts)
        if last:
            self.put('return True')
            return

        part = parts[index]
        not_pred = type(part.pred) is Not
        quant = type(part.quant) is ZeroOrMore

        if type(part.prime) is Char:
            s = f"self._expectc({part.prime})"
        elif type(part.prime) is Identifier:
            s = f'self._{part.prime.string}()'
        elif type(part.prime) is String:
            s = f'self._expects({part.prime})'
        elif type(part.prime) is AnyChar:
            s = 'self._expectc()'
        else:
            raise GeneratorError('unsupported node type', part)

        if quant:
            if not_pred:
                self.put(f'while not {s}:')
            else:
                self.put(f'while {s}:')
            with self.indent():
                self.put('pass')

            self.gen_part(parts, index + 1, length, not_pred)

        else:
            if not_pred:
                self.put(f'if not {s}:')
            else:
                self.put(f'if {s}:')

            with self.indent():
                self.gen_part(parts, index + 1, length, not_pred)
