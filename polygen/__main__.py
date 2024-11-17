import logging

from pathlib import Path
from argparse import ArgumentParser

from polygen.main import (
    logger,
    BACKEND_DIRECTORY,
    PolygenError,
    find_backend_file,
    init_backend,
    generate_parser
)
from polygen.generator.base import CodeGeneratorError

from unittest import TextTestRunner
from polygen.equivalency.test import setUpUnittestSuite


argp = ArgumentParser()
subp = argp.add_subparsers(title="commands")


def cmd_generate_action(ns):
    file = find_backend_file(ns.backend, [BACKEND_DIRECTORY])
    backend_info = init_backend(file, config_options=ns.define,
                                verbose=ns.verbose)

    grammar_file = Path(ns.grammar)
    if not (grammar_file.exists() and grammar_file.is_file()):
        print(f"file {grammar_file} does not exist or not a file")
        return 1

    generate_parser(grammar_file=grammar_file,
                    backend=backend_info,
                    output_directory=Path(ns.output).resolve(),
                    user_options=ns.define,
                    verbose=ns.verbose)


cmd_generate = subp.add_parser("generate")
cmd_generate.add_argument("grammar")
cmd_generate.add_argument("-b", "--backend", required=True,
                          help="backend name")
cmd_generate.add_argument("-o", "--output", required=True,
                          help="output directory")
cmd_generate.add_argument("-d", "--define", action="append", default=[])
cmd_generate.add_argument("-v", "--verbose", action="store_true")
cmd_generate.set_defaults(fn=cmd_generate_action)


def cmd_test_action(ns):
    if ns.verbose:
        logger.setLevel(logging.INFO)
    runner = TextTestRunner()
    runner.run(setUpUnittestSuite(ns.backend))


cmd_test = subp.add_parser("test")
cmd_test.add_argument("-b", "--backend", help="backend name")
cmd_test.add_argument("-v", "--verbose", action="store_true")
cmd_test.set_defaults(fn=cmd_test_action)


def main():
    ns = argp.parse_args()
    try:
        return ns.fn(ns)
    except (PolygenError, CodeGeneratorError) as e:
        print(e)
        return 1


if __name__ == "__main__":
    exit(main())
