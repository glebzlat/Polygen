import re

from contextlib import contextmanager

from polygen.grammar.node import (
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

_UNESCAPED_DOUBLE_QUOTE_RE = re.compile(r'(?<!\\)"')


def wrap_string(s: str):
    if _UNESCAPED_DOUBLE_QUOTE_RE.match(s):
        s = s.replace('"', '\\"')
    return '"' + s + '"'


_LEADING_SPACE_RE = re.compile(r'^\s*')


def reindent(string: str,
             level: int,
             indent='    ') -> str:
    lines = [line for line in string.split('\n') if line.strip()]
    new_indent = indent * level
    base_indent = new_indent

    for line in lines:
        if m := _LEADING_SPACE_RE.match(line):
            if len(m.group()) < len(base_indent):
                base_indent = m.group()

    for i, line in enumerate(lines):
        if line.startswith(base_indent):
            line = line[len(base_indent):]
        lines[i] = new_indent + line

    return '\n'.join(lines)


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

        self.put('@_memoize_lr' if rule.leftrec else '@_memoize')
        self.put(f'def _{rule.id.string}(self):')

        with self.indent():
            self.put('_begin_pos = self._mark()')

            for i, alt in enumerate(rule.expr):
                self.gen_alt(alt, rule, i)

            self.put('return None')

    _INDEXED_VAR_RE = re.compile(r'_\d+')

    def isindexedvar(self, name):
        return self._INDEXED_VAR_RE.match(name) is not None

    def gen_alt(self, alt, rule, alt_index):
        put_newline = len(alt) > 1

        self.put('if (', newline=put_newline)
        variables = []
        with self.indent():
            for i, part in enumerate(alt.parts):
                self.gen_part(part, i, variables, put_newline)
        self.put('):', indent=put_newline)

        with self.indent():
            indent_lvl = len(self.indentation) // 4
            if alt.metarule:
                self.put(f'# {alt.metarule.id.string}')
                self.put(
                    reindent(alt.metarule.expr, level=indent_lvl),
                    indent=0)
            else:
                retval = ', '.join(variables)
                self.put(f'return {retval}' if retval else 'return True')
        self.put('self._reset(_begin_pos)')

    def gen_part(self, part, part_index, variables, newline):
        parts = []

        cond = ''
        if type(part.lookahead) is Not:
            parts += 'self._lookahead', False
        elif type(part.lookahead) is And:
            parts += 'self._lookahead', True
        else:
            cond = 'is not None'

        if type(part.quant) is ZeroOrOne:
            parts.append('self._maybe')
        elif type(part.quant) is ZeroOrMore:
            parts += 'self._loop', False
        elif type(part.quant) is OneOrMore:
            parts += 'self._loop', True

        if type(part.prime) is Char:
            parts += 'self._expectc', part.prime
        elif type(part.prime) is Identifier:
            id = part.prime
            parts.append(f'self._{id.string}')
        elif type(part.prime) is String:
            parts += 'self._expects', part.prime
        elif type(part.prime) is AnyChar:
            parts.append('self._expectc')
        else:
            raise GeneratorError('unsupported node type', part.prime)

        metaname = part.metaname
        if metaname != '_':
            var = metaname
            variables.append(metaname)
        else:
            var = None

        fn, args = parts[0], ', '.join(str(i) for i in parts[1:])
        op = 'and' if part_index else ''
        call = f'{fn}({args})'
        assignment = f'({var} := {call})' if var else call

        string = ' '.join(filter(None, (op, assignment, cond)))
        self.put(string, newline=newline, indent=newline)
