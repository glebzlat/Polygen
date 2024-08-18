import logging
from pathlib import Path

from polygen.parser import Reader, Parser
from polygen.node import DLL, Grammar


logger = logging.getLogger("polygen.gprep")


class GPreprocessorError(Exception):
    pass


def process(grammar_file: Path,
            lookup_dirs: list[Path],
            toplevel=True) -> Grammar:
    logger.info("file %s", grammar_file)
    with open(grammar_file, 'r', encoding="UTF-8") as fin:
        reader = Reader(fin)
        parser = Parser(reader)
        tree = parser.parse()

    if not tree:
        raise GPreprocessorError(f"in file {grammar_file}: parser failed")

    for include in DLL.iter(tree.includes):
        include_path = Path(include.path)
        if include_path.exists():
            subtree = process(include_path, lookup_dirs, False)
        else:
            for dir in lookup_dirs:
                include_path = dir / include_path
                if include_path.exists():
                    logger.info("include found %s", include_path)
                    subtree = process(include_path, lookup_dirs, False)
                    break
            else:
                msg = (
                    f"on {include.filename}: line {include.line}: "
                    f"include path not found: {include.path!r}"
                )
                raise GPreprocessorError(msg)

        tree.merge(subtree)

    return tree
