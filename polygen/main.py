import sys
import logging

from pathlib import Path
from typing import Iterable, Any, Optional

from polygen.parser import Reader, Parser

from polygen.modifier import (
    ModifierVisitor,
    CheckUndefinedRules,
    CheckRedefinedRules,
    ReplaceNestedExprs,
    FindEntryRule,
    CreateAnyChar,
    IgnoreRules,
    GenerateMetanames,
    AssignMetaRules,
    ValidateRangesAndReps,
    ComputeLR
)

from polygen.generator.config import Config

logging.basicConfig(format="{name}: {message}", style="{")
logger = logging.getLogger("polygen")
stdout_handler = logging.StreamHandler(sys.stdout)

CWD = Path(__file__).resolve().parent
BACKEND_DIRECTORY = CWD / "backend"


class FileEvalError(Exception):
    """Error occured in the file evaluation process."""


class BackendSearchError(Exception):
    """Raised if backend is not found or found several backends."""


def create_modifier(*, verbose: bool) -> ModifierVisitor:
    modifier_classes = [
        CheckUndefinedRules,
        CheckRedefinedRules,
        ReplaceNestedExprs,
        FindEntryRule,
        CreateAnyChar,
        IgnoreRules,
        GenerateMetanames,
        AssignMetaRules,
        ValidateRangesAndReps,
        ComputeLR
    ]

    modifiers = []
    for cls in modifier_classes:
        modifiers.append(cls(verbose=verbose))

    return ModifierVisitor(modifiers)


def generate_parser(*,
                    grammar_file: Optional[Path] = None,
                    grammar: Optional[str] = None,
                    backend: str,
                    output_directory: Path,
                    user_options: Optional[Iterable[str]] = None,
                    verbose=False):
    if (
        grammar_file is None and grammar is None or
        grammar_file and grammar
    ):
        raise ValueError("specify either grammar_file or grammar")

    if verbose:
        logger.setLevel(logging.INFO)

    backends = find_backend_file(backend, [BACKEND_DIRECTORY])

    if not backends:
        raise BackendSearchError(f"backend not found: {backend}")
    if len(backends) > 1:
        paths = ', '.join(backends)
        raise BackendSearchError(f"multiple backends found: {paths}")

    if grammar_file:
        with open(grammar_file, 'r', encoding="UTF-8") as fin:
            reader = Reader(fin)
            parser = Parser(reader)
            tree = parser.parse()
    elif grammar:
        reader = Reader(grammar)
        parser = Parser(reader)
        tree = parser.parse()

    modifier = create_modifier(verbose=verbose)
    modifier.apply(tree)

    generator_module = eval_file(backends[0])
    generator_class = generator_module["CodeGenerator"]
    generator_class.backend_dir = backends[0].parent

    config = Config(getattr(generator_class, "OPTIONS", {}),
                    unknown_options="error")
    config.parse(user_options or [])

    gen = generator_class(verbose=verbose)
    gen.generate(tree, config)
    gen.create_files(output_directory)


def bootstrap():
    generate_parser(grammar_file=CWD / "parser.peg",
                    backend="python",
                    output_directory=CWD,
                    user_options=["polygen_imports=true"])


def read_file(filename: Path) -> str:
    with open(filename, 'r', encoding='UTF-8') as fin:
        return fin.read()


def find_backend_file(
    name: str, directories: Iterable[Path]
) -> list[Path]:
    found = []
    for d in directories:
        if not d.exists():
            continue
        backend_dir = d / name
        if not backend_dir.exists():
            continue
        generator_file = backend_dir / "generator.py"
        if generator_file.exists() and generator_file.is_file():
            found.append(generator_file)
    return found


def eval_file(filename: Path) -> dict[str, Any]:
    namespace = {}

    try:
        with open(filename, 'rb') as fin:
            code = compile(fin.read(), filename, 'exec')
            exec(code, namespace)
    except SyntaxError as e:
        raise FileEvalError(f'syntax error in file: {e}') from e
    except SystemExit as e:
        raise FileEvalError('file called sys.exit()') from e
    except Exception as e:
        raise FileEvalError(f'an exception in file: {e}') from e

    return namespace

