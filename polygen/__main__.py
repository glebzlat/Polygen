import sys
import json

from io import StringIO
from argparse import ArgumentParser, FileType, Namespace
from datetime import datetime
from typing import Optional

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

VERSION = "0.0.1"

datetimefmt = "%Y-%m-%d %I:%M %p"

argparser = ArgumentParser()
argparser.add_argument(
    "grammar", type=FileType('r', encoding='utf-8'),
    help="grammar file")
subparsers = argparser.add_subparsers(help="commands", required=True)


def generate_cmd_action(ns: Namespace):
    return generate(ns)


generate_cmd = subparsers.add_parser(
    "generate", help="generate parser from the grammar")
generate_cmd.add_argument(
    "--skeleton", "-s", type=str, help="skeletons directory")
generate_cmd.add_argument(
    "--output", "-o", type=str, help="output directory")
generate_cmd.set_defaults(fn=generate_cmd_action)


def dump_cmd_action(ns: Namespace):
    return dump(ns)


dump_cmd = subparsers.add_parser(
    "dump", help="dump parsed grammar to JSON")
dump_cmd.add_argument(
    "-m", "--modified", action='store_true')
dump_cmd.add_argument(
    "--output", "-o", nargs='?', type=FileType('w', encoding='utf-8'),
    default=sys.stdout, help="output file")
dump_cmd.set_defaults(fn=dump_cmd_action)


def generate(ns: Namespace):
    grammar = parse(ns.grammar)
    if grammar is None:
        print("Parsing failure")
        return 1

    entry_id = modify(grammar)
    if entry_id is None:
        print("Modifier error")
        return 2

    stream = StringIO()
    gen = Generator(stream)
    gen.generate(grammar)
    stream.seek(0)

    directives = {
        "body": stream,
        "entry": f"return self._{entry_id}()",
        "version": VERSION,
        "datetime": datetime.today().strftime(datetimefmt)
    }

    proc = Preprocessor(directives)
    proc.process(ns.skeleton, ns.output)

    return 0


def dump(ns: Namespace):
    grammar = parse(ns.grammar)
    if grammar is None:
        print("Parsing failure")
        return 1

    if ns.modified:
        entry_id = modify(grammar)
        if entry_id is None:
            print("Modifier error")
            return 2

    data = grammar.dump()
    json.dump(data, ns.output, indent=4)

    return 0


def main():
    ns = argparser.parse_args()
    return ns.fn(ns)


def parse(file):
    reader = Reader(file)
    parser = GrammarParser(reader)
    return parser.parse()


def modify(grammar) -> Optional[str]:
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
        return None

    if warnings:
        print(*warnings, sep='\n', file=sys.stderr)

    return find_entry.entry.id.string


exit(main())
