from pathlib import Path

import click

from polygen.main import (
    BACKEND_DIRECTORY,
    PolygenError,
    find_backend_file,
    init_backend,
    generate_parser
)
from polygen.generator.base import CodeGeneratorError


@click.group()
def main():
    pass


@main.command()
@click.argument("grammar", required=True,
                type=click.Path(exists=True, file_okay=True, readable=True,
                                resolve_path=True, path_type=Path))
@click.option("-b", "--backend", required=True, metavar="NAME",
              help="code generator name")
@click.option("-o", "--output", required=True,
              type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("-d", "--define", multiple=True)
@click.option("-v", "--verbose", is_flag=True)
def generate(backend, grammar, output, define, verbose):
    file = find_backend_file(backend, [BACKEND_DIRECTORY])
    backend_info = init_backend(file, config_options=define, verbose=verbose)
    generate_parser(grammar_file=grammar,
                    backend=backend_info,
                    output_directory=Path(output).resolve(),
                    user_options=define,
                    verbose=verbose)


if __name__ == "__main__":
    try:
        main()
    except (PolygenError, CodeGeneratorError) as e:
        print(e)
        exit(1)
