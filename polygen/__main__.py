import sys

from io import StringIO
from argparse import ArgumentParser, FileType
from datetime import datetime

from .reader import Reader
from .grammar_parser import GrammarParser
from .tree_transformer import (
    ExpandClass,
    ReplaceRep,
    ReplaceZeroOrOne,
    ReplaceOneOrMore,
    EliminateAnd,
    CheckUndefRedef,
    SimplifyNestedExps,
    ReplaceNestedExps,
    CreateAnyCharRule,
    FindEntryRule,
    TreeModifier
)

from .generate_python import Generator
from .preprocessor import Preprocessor

datetimefmt = "%Y-%m-%d %I:%M %p"

argparser = ArgumentParser()
argparser.add_argument("--grammar", "-g", type=FileType('r', encoding='utf-8'),
                       help="Grammar file")
argparser.add_argument("--skeleton", "-s", type=str, help="Skeletons directory")
argparser.add_argument("--output", "-o", type=str, help="Output directory")

VERSION = "0.0.1"


def main():
    ns = argparser.parse_args()

    reader = Reader(ns.grammar)
    parser = GrammarParser(reader)
    grammar = parser.parse()

    find_entry = FindEntryRule()

    write_rules = [
        [CreateAnyCharRule()],
        [
            ExpandClass(),
            ReplaceRep(),
            ReplaceZeroOrOne()
        ],
        [EliminateAnd()],
        [CheckUndefRedef()],
        [ReplaceOneOrMore(), ReplaceNestedExps()],
        [find_entry],
        [SimplifyNestedExps()],
    ]

    modifier = TreeModifier(write_rules)
    success, errors, warnings = modifier.visit(grammar)

    if not success:
        print(*errors, sep='\n', file=sys.stderr)
        return 1

    if warnings:
        print(*warnings, sep='\n', file=sys.stderr)

    stream = StringIO()
    gen = Generator(stream)
    gen.generate(grammar)
    stream.seek(0)

    directives = {
        "body": stream,
        "entry": f"return self._{find_entry.entry.id.string}()",
        "version": VERSION,
        "datetime": datetime.today().strftime(datetimefmt)
    }

    proc = Preprocessor(directives)

    proc.process(ns.skeleton, ns.output)

    return 0


exit(main())
