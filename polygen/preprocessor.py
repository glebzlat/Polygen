import logging

from pathlib import Path
from typing import Optional

from polygen.parser import Reader, Parser
from polygen.node import (
    DLL,
    Grammar,
    Include,
    Entry,
    ToplevelQuery,
    BackendQuery,
    BackendDef,
    Ignore
)
from polygen.generator.base import CodeGeneratorBase
from polygen.utility import reindent


logger = logging.getLogger("polygen.gprep")


class GPreprocessorError(Exception):
    pass


class IncludeNotFound(GPreprocessorError):
    pass


class CircularIncludeError(GPreprocessorError):
    pass


class UnknownEntry(GPreprocessorError):
    pass


def process(grammar_file: Path,
            lookup_dirs: list[Path],
            backend_name: str,
            generator: CodeGeneratorBase):
    return _process(
        grammar_file,
        lookup_dirs,
        backend_name,
        generator,
        True,
        set()
    )


def _process(grammar_file: Path,
             lookup_dirs: list[Path],
             backend_name: str,
             generator: CodeGeneratorBase,
             toplevel: bool,
             included_paths: set[Path]) -> Grammar:
    logger.info("file %s", grammar_file)
    with open(grammar_file, 'r', encoding="UTF-8") as fin:
        reader = Reader(None)
        parser = Parser(reader)
        tree: Grammar = parser.parse(fin)

    return _process_grammar(
        tree,
        None,
        lookup_dirs,
        backend_name,
        generator,
        toplevel,
        included_paths
    )


def _process_grammar(tree: Grammar,
                     outer_tree: Optional[Grammar],
                     lookup_dirs: list[Path],
                     backend_name: str,
                     generator: CodeGeneratorBase,
                     toplevel: bool,
                     included_paths: set[Path]) -> Grammar:
    for directive in DLL.iter(tree.directives):
        if isinstance(directive, Include):
            include_path = Path(directive.path)
            if not include_path.exists():
                for dir in lookup_dirs:
                    include_path = dir / include_path
                    if include_path.exists():
                        logger.info("include found %s", include_path)
                        break
                else:
                    msg = (
                        f"on {directive.filename}: line {directive.line}: "
                        f"include path not found: {directive.path!r}"
                    )
                    raise IncludeNotFound(msg)

            if include_path in included_paths:
                msg = (
                    f"circular include: in {directive.filename}: "
                    f"line: {directive.line}: {include_path}"
                )
                raise CircularIncludeError(msg)

            included_paths.add(include_path)
            subtree = _process(
                include_path,
                lookup_dirs,
                backend_name,
                generator,
                False,
                included_paths
            )
            tree.merge(subtree)

        elif isinstance(directive, Entry):
            id = directive.id

            for rule in DLL.iter(tree.rules):
                if rule.id == id:
                    rule.entry = True
                    break
            else:
                rules = outer_tree.rules if outer_tree else None
                for rule in DLL.iter(rules):
                    if rule.id == id:
                        rule.entry = True
                        break
                else:
                    msg = (
                        f"no rule with the name {directive.id} found in"
                        f"{directive.filename}: on line {directive.line}"
                    )
                    raise UnknownEntry(msg)

        elif isinstance(directive, ToplevelQuery):
            if not toplevel:
                continue

            subtree = _process_grammar(
                directive.grammar,
                tree,
                lookup_dirs,
                backend_name,
                generator,
                False,
                included_paths,
            )
            tree.merge(subtree)

        elif isinstance(directive, BackendQuery):
            if directive.name.value != backend_name:
                continue

            subtree = _process_grammar(
                directive.grammar,
                tree,
                lookup_dirs,
                backend_name,
                generator,
                False,
                included_paths,
            )
            tree.merge(subtree)

        elif isinstance(directive, BackendDef):
            with generator.directive(directive.id.value):
                generator.put(reindent(directive.expr, 0))

        elif isinstance(directive, Ignore):
            ids = set(directive.ids)
            for rule in DLL.iter(tree.rules):
                if rule.id in ids:
                    rule.ignore = True

    return tree
