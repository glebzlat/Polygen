import logging
from pathlib import Path

from polygen.parser import Reader, Parser
from polygen.node import DLL, Grammar


logger = logging.getLogger("polygen.gprep")


class GPreprocessorError(Exception):
    pass


class ParserFailed(GPreprocessorError):
    pass


class IncludeNotFound(GPreprocessorError):
    pass


class CircularIncludeError(GPreprocessorError):
    pass


def process(grammar_file: Path, lookup_dirs: list[Path]):
    return _process(grammar_file, lookup_dirs, True, set())


def _process(grammar_file: Path,
             lookup_dirs: list[Path],
             toplevel: bool,
             included_paths: set[Path]) -> Grammar:
    logger.info("file %s", grammar_file)
    with open(grammar_file, 'r', encoding="UTF-8") as fin:
        reader = Reader(fin)
        parser = Parser(reader)
        tree = parser.parse()

    if not tree:
        raise ParserFailed(f"in file {grammar_file}: parser failed")

    for include in DLL.iter(tree.includes):
        include_path = Path(include.path)
        if not include_path.exists():
            for dir in lookup_dirs:
                include_path = dir / include_path
                if include_path.exists():
                    logger.info("include found %s", include_path)
                    break
            else:
                msg = (
                    f"on {include.filename}: line {include.line}: "
                    f"include path not found: {include.path!r}"
                )
                raise IncludeNotFound(msg)

        if include_path in included_paths:
            msg = (
                f"circular include: in {include.filename}: "
                f"line: {include.line}: {include_path}"
            )
            raise CircularIncludeError(msg)

        included_paths.add(include_path)
        subtree = _process(include_path, lookup_dirs, False, included_paths)

        tree.merge(subtree)

    return tree
