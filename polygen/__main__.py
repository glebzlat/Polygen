import sys

from argparse import ArgumentParser, FileType

from .reader import Reader
from .grammar_parser import GrammarParser
from .tree_transformer import (
    ExpandClassRule,
    ReplaceRepRule,
    ReplaceZeroOrOneRule,
    ReplaceOneOrMore,
    EliminateAndRule,
    CheckUndefRedefRule,
    SimplifyNestedExps,
    ReplaceNestedExpsRule,
    CreateAnyCharRule,
    TreeTransformer
)

from .generate_python import Generator

argparser = ArgumentParser()
argparser.add_argument("file", nargs='?', type=FileType('r', encoding='utf-8'),
                       default=sys.stdin)
repr_types = argparser.add_mutually_exclusive_group()
repr_types.add_argument("--str", "-s", action='store_true')
repr_types.add_argument("--repr", "-r", action='store_true')
repr_types.add_argument("--descendants", "-d", action='store_true')
repr_types.add_argument("--convert", "-c", action='store_true')
repr_types.add_argument("--generate", "-g", action='store_true')


def main():
    ns = argparser.parse_args()

    reader = Reader(ns.file)
    parser = GrammarParser(reader)
    grammar = parser.parse()

    if ns.repr:
        print(repr(grammar))

    elif ns.descendants:
        for node in map(repr, grammar.descendants):
            print(node)

    elif ns.convert or ns.generate:
        write_rules = [
            [CreateAnyCharRule()],
            [
                ExpandClassRule(),
                ReplaceRepRule(),
                ReplaceZeroOrOneRule()
            ],
            [EliminateAndRule()],
            [CheckUndefRedefRule()],
            [ReplaceOneOrMore(), ReplaceNestedExpsRule()],
            [SimplifyNestedExps()],
        ]
        writer = TreeTransformer(write_rules)
        success, errors, warnings = writer.traverse(grammar)

        if ns.convert:
            if not success:
                print(*errors, sep='\n')

            for rule in grammar:
                print(repr(rule), end='\n\n')
        else:
            gen = Generator()
            gen.generate(grammar)

    else:
        print(grammar)

    return 0


exit(main())
