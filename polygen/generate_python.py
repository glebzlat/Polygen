from contextlib import contextmanager

from .node import (
    Grammar,
    Rule,
    Identifier,
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
    def indent(self, level: int = 1):
        save = self.indentation
        try:
            self.indentation += '    ' * level
            yield
        finally:
            self.indentation = save

    def join(self, *parts: str):
        return '\n'.join(self.indentation + s for s in parts)

    def generate(self, grammar: Grammar):
        for i, rule in enumerate(grammar):
            self.gen_rule(i, rule)

    def gen_rule(self, index: int, rule: Rule):
        if index:
            self.putni()
        self.put('@memoize')
        self.put(f'def _{rule.name.string}(self):')

        # Check for the last empty alternative, signaling that there is
        # a desugared ZeroOrOne quantifier. If the last is empty, do not
        # save and restore current position
        last_alt = rule.rhs.alts[-1]
        last_alt_length = len(last_alt)

        with self.indent():
            if last_alt_length != 0:
                self.put('pos = self._mark()')

            for alt in rule.rhs:
                last_idx = len(alt) - 1

                return_level, cleanup_level = None, None

                level = 0
                for i, part in enumerate(alt):
                    with self.indent(level):
                        level += self.gen_part(part, level, last_idx)

                        if i == last_idx:
                            return_level = level

                        # if this alternative is not the last, then
                        # it should perform cleanup for the next alternative
                        elif i == 0 and alt is not last_alt:
                            cleanup_level = level

                if return_level is not None:
                    with self.indent(return_level):
                        self.put('return True')

                if cleanup_level is not None:
                    with self.indent(cleanup_level):
                        self.put('self._reset(pos)')

            if last_alt_length == 0:
                self.put('return True')
            else:
                self.put('self._reset(pos)')
                self.put('return False')

    def gen_part(self, part, index: int, last_index: int) -> int:
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

            return 0

        else:
            if not_pred:
                self.put(f'if not {s}:')
            else:
                self.put(f'if {s}:')

            return 1
