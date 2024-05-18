import sys
import json

from argparse import ArgumentParser, FileType, Namespace
from itertools import zip_longest

from .generator import Generator

argparser = ArgumentParser()
argparser.add_argument(
    "grammar", type=FileType('r', encoding='utf-8'),
    help="grammar file")
subparsers = argparser.add_subparsers(help="commands", required=True)


def generate_cmd_action(gen: Generator, ns: Namespace):
    output = ((None if i == '_' else i) for i in ns.output)
    files = list(zip_longest(ns.input, output))
    print(files)
    gen.generate(ns.grammar, files)


generate_cmd = subparsers.add_parser(
    "generate", help="generate parser from the grammar")
generate_cmd.add_argument("--input", "-i", type=str, required=True, nargs='+',
                          help="list of input files")
generate_cmd.add_argument("--output", "-o", type=str, nargs='*',
                          help="list of output files")
generate_cmd.set_defaults(fn=generate_cmd_action)


def dump_cmd_action(gen: Generator, ns: Namespace):
    grammar = gen.get_grammar(ns.grammar, modified=ns.modified)
    json.dump(grammar.to_dict(), ns.output, indent=4)


dump_cmd = subparsers.add_parser(
    "dump", help="dump parsed grammar to JSON")
dump_cmd.add_argument(
    "-m", "--modified", action='store_true')
dump_cmd.add_argument(
    "--output", "-o", nargs='?', type=FileType('w', encoding='utf-8'),
    default=sys.stdout, help="output file")
dump_cmd.set_defaults(fn=dump_cmd_action)


def main():
    ns = argparser.parse_args()
    gen = Generator()

    ns.fn(gen, ns)

    return 0


exit(main())
