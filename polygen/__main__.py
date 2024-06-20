import sys

from argparse import ArgumentParser, FileType, Namespace
from pathlib import Path

from .codegen import CodeGenerator
from .modifier.registry import ModifierRegistry, parse_modifier_options
from .parser import Parser as GrammarParser
from .modifier.tree_modifier import TreeModifier

argparser = ArgumentParser()
subparsers = argparser.add_subparsers(help="commands", required=True)


def generate_cmd_action(gen: CodeGenerator, ns: Namespace):
    define = ns.define or []
    options = {}
    for defn in define:
        opt, value = defn.split('=')
        options[opt] = value
    gen.generate(ns.backend, ns.output, options=options, grammar=ns.grammar)


generate_cmd = subparsers.add_parser(
    "generate", help="generate parser from the grammar")
generate_cmd.add_argument(
    "-b", "--backend", type=str, required=True,
    help="code generator")
generate_cmd.add_argument(
    "-g", "--grammar-file", type=FileType('r', encoding='utf-8'),
    help="grammar file",
    dest="grammar")
generate_cmd.add_argument(
    "-o", "--output", type=str, help="output directory")
generate_cmd.add_argument("--define", "-D", action="append")
generate_cmd.set_defaults(fn=generate_cmd_action)


def list_backends_action(gen: CodeGenerator, ns: Namespace):
    backends = gen.backends_info()
    for name, (lang, ver) in backends.items():
        print(f"{name}: {lang} {ver}")


list_cmd = subparsers.add_parser(
    "list-backends", help="list available code generators")
list_cmd.set_defaults(fn=list_backends_action)


def render_grammar_action(gen: CodeGenerator, ns: Namespace):
    parser = GrammarParser(ns.grammar)
    grammar = parser.parse()
    if grammar is None:
        return
    grammar = grammar.value

    registry = ModifierRegistry()
    modifiers = parse_modifier_options(registry, ns.options)

    visitor = TreeModifier(modifiers)

    warn = None
    try:
        visitor.apply(grammar)
    except Warning as w:
        warn = w

    if ns.repr:
        print(repr(grammar))
    else:
        print(grammar)

    if warn:
        print()
        print(warn)


render_cmd = subparsers.add_parser(
    "render", help="print the grammar")
render_cmd.add_argument(
    "-b", "--backend", type=str, required=True, help="code generator")
render_cmd.add_argument(
    "-g", "--grammar-file", type=FileType('r', encoding='utf-8'),
    required=True,
    help="grammar file",
    dest="grammar")
render_cmd.add_argument(
    "-d", "--def", type=str, action='append',
    dest="options",
    help="define option for the TreeRegistry"
)
render_cmd.add_argument(
    "-o", "--output", type=FileType('w', encoding='utf-8'),
    default=sys.stdout,
    help="output stream (default: stdout)")
render_cmd.add_argument("-r", "--repr", action='store_true')
render_cmd.set_defaults(fn=render_grammar_action)


def main():
    gen = CodeGenerator.setup()

    ns = argparser.parse_args()
    ns.fn(gen, ns)

    return 0


exit(main())
