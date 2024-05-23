import unittest

from collections import Counter

from polygen.grammar.node import (
    Node,
    # Grammar,
    # Expression,
    # Rule,
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
                # print(dct_repr)
                self.assertEqual(dct_repr, dct_clue)

                node_clue = eval(r_clue)
                self.assertEqual(node, node_clue)

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
         {'type': 'Char', 'code': 97, 'begin_pos': 0}),
        (Char(0x03c0),
         "Char('\\u03c0')",
         "'\\u03c0'",
         {'type': 'Char', 'code': 0x03c0, 'begin_pos': 0})
    ]


class TestStringRepr(NodeReprTest):

    cases = [
        (String(Char('a'), Char('b'), Char('c')),
         "String(Char('a'), Char('b'), Char('c'))",
         '"abc"',
         {'type': 'String',
          'chars': [{'begin_pos': 0, 'code': 97, 'type': 'Char'},
                    {'begin_pos': 0, 'code': 98, 'type': 'Char'},
                    {'begin_pos': 0, 'code': 99, 'type': 'Char'}],
          'begin_pos': 0})
    ]


class TestRangeRepr(NodeReprTest):

    cases = [
        (Range(Char('a')),
         "Range(Char('a'))",
         "Range('a')",
         {'type': 'Range',
          'beg': {'type': 'Char',
                  'code': ord('a'),
                  'begin_pos': 0},
          'end': None,
          'begin_pos': 0}),
        (Range(Char('a'), Char('b')),
         "Range(Char('a'), Char('b'))",
         "Range('a', 'b')",
         {'type': 'Range',
          'beg': {'type': 'Char',
                  'code': ord('a'),
                  'begin_pos': 0},
          'end': {'type': 'Char',
                  'code': ord('b'),
                  'begin_pos': 0},
          'begin_pos': 0})
    ]


class TestClassRepr(NodeReprTest):

    cases = [
        (Class(Range(Char('a'))),
         "Class(Range(Char('a')))",
         "Class(Range('a'))",
         {'type': 'Class',
          'ranges': [
              {'type': 'Range',
               'beg': {'type': 'Char',
                       'code': ord('a'),
                       'begin_pos': 0},
               'end': None,
               'begin_pos': 0}
          ],
          'begin_pos': 0}
         )
    ]


class TestRepetitionRepr(NodeReprTest):

    cases = [
        (Repetition(1, 2),
         "Repetition(1, 2)",
         "Repetition(1, 2)",
         {'type': 'Repetition', 'beg': 1, 'end': 2,
          'begin_pos': 0}),
        (Repetition(1),
         "Repetition(1)",
         "Repetition(1)",
         {'type': 'Repetition', 'beg': 1, 'end': None,
          'begin_pos': 0})
    ]


class TestZeroOrOneRepr(NodeReprTest):

    cases = [
        (ZeroOrOne(),
         "ZeroOrOne()",
         "ZeroOrOne",
         {'type': 'ZeroOrOne', 'begin_pos': 0})
    ]


class TestZeroOrMoreRepr(NodeReprTest):

    cases = [
        (ZeroOrMore(),
         "ZeroOrMore()",
         "ZeroOrMore",
         {'type': 'ZeroOrMore', 'begin_pos': 0})
    ]


class TestOneOrMoreRepr(NodeReprTest):

    cases = [
        (OneOrMore(),
         "OneOrMore()",
         "OneOrMore",
         {'type': 'OneOrMore', 'begin_pos': 0})
    ]


class TestAndRepr(NodeReprTest):

    cases = [
        (And(),
         "And()",
         "And",
         {'type': 'And', 'begin_pos': 0})
    ]


class TestNotRepr(NodeReprTest):

    cases = [
        (Not(),
         "Not()",
         "Not",
         {'type': 'Not', 'begin_pos': 0})
    ]


class TestAnyCharRepr(NodeReprTest):

    cases = [
        (AnyChar(),
         "AnyChar()",
         "AnyChar",
         {'type': 'AnyChar', 'begin_pos': 0})
    ]


class TestIdentifierRepr(NodeReprTest):

    cases = [
        (Identifier("name"),
         "Identifier('name')",
         "Identifier(name)",
         {'type': 'Identifier', 'string': 'name', 'begin_pos': 0})
    ]


class TestPartRepr(NodeReprTest):

    # XXX: Part's begin_pos?
    cases = [
        (Part(prime=Char('a')),
         "Part(prime=Char('a'))",
         "Part(prime='a')",
         {'type': 'Part',
          'lookahead': None,
          'quant': None,
          'metaname': None,
          'prime': {'type': 'Char',
                    'code': ord('a'),
                    'begin_pos': 0}
          }
         )
    ]


class TestAltRepr(NodeReprTest):

    cases = [
        (Alt(Part(prime=Char('a'))),
         "Alt(Part(prime=Char('a')))",
         "Alt(Part(prime='a'))",
         {'type': 'Alt',
          'metarule': None,
          'parts': [
              {'type': 'Part',
               'lookahead': None,
               'quant': None,
               'metaname': None,
               'prime': {'type': 'Char',
                         'code': ord('a'),
                         'begin_pos': 0}}]})
    ]


class TestMetaRefRepr(NodeReprTest):

    # XXX: MetaRef's begin_pos?
    cases = [
        (MetaRef(Identifier('ref')),
         "MetaRef(Identifier('ref'))",
         "MetaRef(Identifier(ref))",
         {'type': 'MetaRef',
          'id': {'type': 'Identifier',
                 'string': 'ref',
                 'begin_pos': 0}})
    ]


class TestMetaRuleRepr(NodeReprTest):

    # XXX: MetaRule's begin_pos?
    cases = [
        (MetaRule(expr='expr'),
         "MetaRule(expr='expr')",
         "MetaRule(expr=expr)",
         {'type': 'MetaRule',
          'id': None,
          'expr': 'expr'}),
        (MetaRule(id=Identifier('id'), expr='expr'),
         "MetaRule(id=Identifier('id'), expr='expr')",
         "MetaRule(id=Identifier(id), expr=expr)",
         {'type': 'MetaRule',
          'id': {'type': 'Identifier',
                 'string': 'id',
                 'begin_pos': 0},
          'expr': 'expr'})
    ]
