import sys
import logging

from pathlib import Path
from typing import Iterable, Any, Optional, Iterator, Type

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
from polygen.generator.base import CodeGeneratorBase
from polygen.generator.runner import RunnerBase

logging.basicConfig(format="{name}: {message}", style="{")
logger = logging.getLogger("polygen")
stdout_handler = logging.StreamHandler(sys.stdout)

CWD = Path(__file__).resolve().parent
BACKEND_DIRECTORY = CWD / "backend"


class PolygenError(Exception):
    pass


class FileEvalError(PolygenError):
    """Error occured in the file evaluation process."""


class BackendNotFound(PolygenError):
    pass


class Backend:
    def __init__(self,
                 generator: CodeGeneratorBase,
                 runner: RunnerBase,
                 config: Config):
        self.generator = generator
        self.runner = runner
        self.config = config


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
                    backend: Backend,
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

    backend.generator.generate(tree, backend.config)
    output_files = backend.generator.create_files(output_directory)
    backend.runner.output_files = output_files
    backend.generator.cleanup()


def find_backend_file(
    name: str, directories: Iterable[Path]
) -> Path:
    searched = []
    for d in directories:
        if not d.exists():
            continue
        backend_dir = d / name
        if not backend_dir.exists():
            searched.append(d)
            continue
        generator_file = backend_dir / "backend.py"
        if not (generator_file.exists() and generator_file.is_file()):
            searched.append(d)
            continue
        return generator_file

    paths = "\n".join(map(str, searched))
    raise BackendNotFound(f"backend {name} not found in:\n{paths}")


def init_backend(file: Path,
                 config_options: Iterable[str],
                 verbose=False) -> Backend:
    namespace: dict[str, Any] = eval_file(file)

    gen_class: Type[CodeGeneratorBase] = namespace["CodeGenerator"]
    runner_class: Type[RunnerBase] = namespace["Runner"]
    gen_class.backend_dir = file.parent
    config = Config(gen_class.OPTIONS)

    config.parse(config_options)
    backend = Backend(gen_class(verbose=verbose), runner_class(), config)

    return backend


def iterate_backend_files(directories: Iterable[Path]) -> Iterator[Path]:
    for d in directories:
        if not d.exists():
            continue
        for sub in d.iterdir():
            if not sub.exists() or not sub.is_dir():
                continue
            generator_file = sub / "backend.py"
            if generator_file.exists() and generator_file.is_file():
                yield generator_file


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

