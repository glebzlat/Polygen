import unittest

from collections import Counter

from polygen.grammar.node import (
    Node,
    Grammar,
    Expression,
    Rule,
    MetaRef,
    MetaRule,
    Identifier,
    Range,
    Alt,
    Part,
    AnyChar,
    String,
    Class,
    Not,
    And,
    ZeroOrOne,
    ZeroOrMore,
    OneOrMore,
    Repetition,
    Char
)


class NodeReprTestMetaclass(type):
    def __init__(cls, name, bases, body):
        if name == 'NodeReprTest':
            return

        cases: list[tuple[Node, str, str, dict]] = getattr(cls, 'cases')

        node_types = Counter()
        for i, (node, r_clue, s_clue, dct_clue) in enumerate(cases):

            def test_repr(self):
                dct_repr = node.to_dict()
                self.assertEqual(dct_repr, dct_clue)

                r = repr(node)
                self.assertEqual(r, r_clue)

                s = str(node)
                self.assertEqual(s, s_clue)

            node_type = type(node)
            node_name = node_type.__name__

            if node_type in node_types:
                count = node_types[node_type]
                method_name = f'test_{node_name}_{count}'
            else:
                method_name = f'test_{node_name}'

            setattr(cls, method_name, test_repr)
            node_types[node_type] += 1


bases = (unittest.TestCase,)
NodeReprTest = NodeReprTestMetaclass('NodeReprTest', bases, {})


class TestCharRepr(NodeReprTest):

    cases = [
        (Char('a'),
         "Char('a')",
         "'a'",
         {'type': 'Char', 'code': 97, 'begin_pos': 0, 'end_pos': 0}),
        (Char(0x03c0),
         "Char('\\\\u03c0')",
         "\\u03c0",
         {'type': 'Char', 'code': 0x03c0, 'begin_pos': 0, 'end_pos': 0})
    ]


class TestStringRepr(NodeReprTest):

    cases = [
        (String(Char('a'), Char('b'), Char('c')),
         "String(Char('a'), Char('b'), Char('c'))",
         '"abc"',
         {'type': 'String',
          'chars': [{'begin_pos': 0, 'code': 97, 'end_pos': 0, 'type': 'Char'},
                    {'begin_pos': 0, 'code': 98, 'end_pos': 0, 'type': 'Char'},
                    {'begin_pos': 0, 'code': 99, 'end_pos': 0, 'type': 'Char'}],
          'begin_pos': 0,
          'end_pos': 0})
    ]


class TestRepetitionRepr(NodeReprTest):

    cases = [
        (Repetition(1, 2),
         "Repetition(1, 2)",
         "Repetition(1, 2)",
         {'type': 'Repetition', 'beg': 1, 'end': 2,
          'begin_pos': 0, 'end_pos': 0}),
        (Repetition(1),
         "Repetition(1)",
         "Repetition(1)",
         {'type': 'Repetition', 'beg': 1, 'end': None,
          'begin_pos': 0, 'end_pos': 0})
    ]
