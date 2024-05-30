from argparse import ArgumentParser, FileType, Namespace
from pathlib import Path

from .codegen import Generator

argparser = ArgumentParser()
subparsers = argparser.add_subparsers(help="commands", required=True)


def generate_cmd_action(gen: Generator, ns: Namespace):
    define = ns.define or []
    options = {}
    for defn in define:
        opt, value = defn.split('=')
        options[opt] = value
    gen.generate(ns.backend, ns.output, options=options, grammar=ns.grammar)


generate_cmd = subparsers.add_parser(
    "generate", help="generate parser from the grammar")
generate_cmd.add_argument("backend", type=str)
generate_cmd.add_argument(
    "grammar", type=FileType('r', encoding='utf-8'),
    help="grammar file")
generate_cmd.add_argument(
    "output", type=str, help="output directory")
generate_cmd.add_argument("--define", "-D", action="append")
generate_cmd.set_defaults(fn=generate_cmd_action)


def list_backends_action(gen: Generator, ns: Namespace):
    backends = gen.backends_info()
    for name, (lang, ver) in backends.items():
        print(f"{name}: {lang} {ver}")


list_cmd = subparsers.add_parser(
    "list-backends", help="list available code generators")
list_cmd.set_defaults(fn=list_backends_action)


def main():
    gen = Generator.setup()

    ns = argparser.parse_args()
    ns.fn(gen, ns)

    return 0


exit(main())
