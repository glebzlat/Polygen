import sys

from argparse import ArgumentParser, FileType

from .reader import Reader
from .grammar_parser import GrammarParser

argparser = ArgumentParser()
argparser.add_argument("file", nargs='?', type=FileType('r', encoding='utf-8'),
                       default=sys.stdin)


def main():
    ns = argparser.parse_args()

    reader = Reader(ns.file)
    parser = GrammarParser(reader)
    print(parser.parse())

    return 0


exit(main())
