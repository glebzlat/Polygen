import sys

from argparse import ArgumentParser, FileType

from .reader import Reader
from .grammar_parser import GrammarParser

argparser = ArgumentParser()
argparser.add_argument("file", nargs='?', type=FileType('r', encoding='utf-8'),
                       default=sys.stdin)
repr_types = argparser.add_mutually_exclusive_group()
repr_types.add_argument("--str", "-s", action='store_true')
repr_types.add_argument("--repr", "-r", action='store_true')
repr_types.add_argument("--descendants", "-d", action='store_true')


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
    else:
        print(grammar)

    return 0


exit(main())
