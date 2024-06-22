import click

from .codegen import CodeGenerator
from .config import ConfigError
from .modifier.registry import RegistryError

gen = CodeGenerator.setup()


@click.group()
def main():
    pass


@main.command()
@click.argument("grammar", required=True,
                type=click.File('r', encoding='UTF-8'))
@click.option("-b", "--backend", required=True, metavar="NAME",
              help="code generator name")
@click.option("-o", "--output", required=True,
              type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("-d", "--define", multiple=True)
def generate(backend, grammar, output, define):
    mod_opts = gen.registry.parse_modifier_options(define)
    gen.generate(backend, output, modifier_options=mod_opts, grammar=grammar)


@main.command()
def list_backends():
    for name, (lang, ver) in gen.backends_info().items():
        click.echo(f"{name}: {lang} {ver}")


@main.command()
def list_modifiers():
    for name, cfg in gen.registry.schema.items():
        public_options = {name: opt for name, opt in cfg.schema.items()
                          if not name.startswith('_')}
        if public_options:
            click.echo(f"{name}:")
            for n, o in public_options.items():
                print(f"  {n}: {o.type.__name__}")
        else:
            click.echo(name)


@main.command()
@click.argument("grammar", required=True,
                type=click.File('r', encoding='UTF-8'))
@click.option("-d", "--define", multiple=True)
@click.option("-r", "--repr", "use_repr", is_flag=True,
              help="`repr` grammar format")
@click.option("-o", "--output",
              type=click.File('w', encoding='UTF-8', lazy=True),
              help="output file; default stdout")
def render_grammar(grammar, define, use_repr, output):
    mod_opts = gen.registry.parse_modifier_options(define)
    tree = gen.get_grammar_tree(grammar, mod_opts)
    click.echo(repr(tree) if use_repr else str(tree), file=output)


if __name__ == "__main__":
    try:
        main()
    except ConfigError as e:
        print(f"Config error: {e}")
        exit(1)
    except RegistryError as e:
        print(f"User option parsing error: {e}")
        exit(1)
