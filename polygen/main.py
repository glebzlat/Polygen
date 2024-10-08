import sys
import logging
import tracemalloc
import linecache
import time
import os
import traceback

from pathlib import Path
from typing import Iterable, Any, Optional, Iterator, Type

# from polygen.parser import Reader, Parser
from polygen.preprocessor import process, GPreprocessorError

from polygen.modifier import (
    Options,
    TreeModifierWarning,
    SemanticError,
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

include_paths = ()
if "POLYGEN_INCLUDE_PATH" in os.environ:
    var = os.environ["POLYGEN_INCLUDE_PATH"]
    include_paths = tuple(Path(p) for p in var.split(':'))


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


def create_modifier(*, reserved_words: set[str]) -> ModifierVisitor:
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

    options = Options(reserved_words=reserved_words)
    modifiers = []
    for cls in modifier_classes:
        modifiers.append(cls(options))

    return ModifierVisitor(modifiers)


def generate_parser(*,
                    grammar_file: Optional[Path] = None,
                    backend: Backend,
                    output_directory: Path,
                    user_options: Optional[Iterable[str]] = None,
                    verbose=False):
    if verbose:
        logger.setLevel(logging.INFO)

    if logger.isEnabledFor(logging.DEBUG) or logger.isEnabledFor(logging.INFO):
        tracemalloc.start()
        t1 = time.perf_counter()

    try:
        tree = process(
            grammar_file,
            [Path.cwd(), *include_paths],
            backend.generator.NAME,
            backend.generator
        )
    except GPreprocessorError as e:
        logger.error("grammar preprocessor error: %s", e)
        return
    except SyntaxError as e:
        msg = '\n' + ''.join(traceback.format_exception(SyntaxError, e, None))
        logger.error(msg)
        return

    try:
        modifier = create_modifier(
            reserved_words=backend.generator.RESERVED_WORDS
        )
        modifier.apply(tree)
    except TreeModifierWarning as w:
        logger.warn(str(w))
    except SemanticError as e:
        logger.error(str(e))
        return

    backend.generator.generate(tree, backend.config)
    files = backend.generator.create_files(output_directory)
    backend.runner.parser_files = files
    backend.generator.cleanup()

    if logger.isEnabledFor(logging.DEBUG) or logger.isEnabledFor(logging.INFO):
        t2 = time.perf_counter()
        dt = t2 - t1
        logger.info(f"total time: {dt:.3f} sec")
        snapshot = tracemalloc.take_snapshot()
        display_memory_usage(snapshot)


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


def display_memory_usage(snapshot: tracemalloc.Snapshot, lines_limit=10):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>")
    ))

    if logger.isEnabledFor(logging.DEBUG):
        top_stats = snapshot.statistics("lineno")
        lines = [f"top {lines_limit} memory consumptive lines:"]
        for index, stat in enumerate(top_stats[:lines_limit], 1):
            frame, size = stat.traceback[0], stat.size / 1024
            s = f"# {index}: {frame}:{frame.lineno}: {size:.1f} KiB"
            lines.append(s)
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                lines.append(f"  {line}")

        other = top_stats[lines_limit:]
        if other:
            size = sum(stat.size for stat in other) / 1024
            lines.append(f"{len(other)} other: {size:.1f} KiB")

        total = sum(stat.size for stat in top_stats) / 1024
        lines.append(f"total allocated size: {total:.1f} KiB")

        message = '\n'.join(lines)
        logger.debug(message)

    elif logger.isEnabledFor(logging.INFO):
        stats = snapshot.statistics("filename")
        size = sum(stat.size for stat in stats) / 1024
        logger.info(f"allocated memory: {size:.1f} KiB")
