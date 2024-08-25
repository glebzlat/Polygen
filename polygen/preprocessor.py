import logging

from pathlib import Path
from collections import deque

from polygen.parser import Reader, Parser
from polygen.node import (
    DLL,
    Grammar,
    Directive,
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
    toplevel_include = Include(str(grammar_file), 0, "<preprocessor>")
    queue = deque([toplevel_include])
    tree = None

    reader = Reader(None)
    parser = Parser(reader)

    file_number = 0
    included = set()
    deferred = []

    # breakpoint()
    while queue:
        include = queue.popleft()
        if include in included:
            # Prevent files that were already included by the another branch
            # from being included more than once.
            continue
        file = _find_include_path(include, lookup_dirs)

        includes, df, subtree = _process(
            parser,
            file,
            lookup_dirs,
            backend_name,
            generator,
            file_number == 0
        )
        deferred.extend(df)

        included.add(include)
        for i in includes:
            if i == include or i in queue:
                msg = (
                    f"circular include: in {i.filename}:\n"
                    f"line: {i.line}: {i.path}"
                )
                raise CircularIncludeError(msg)
            queue.append(i)

        if not tree:
            tree = subtree
        elif tree is not subtree:
            tree.merge(subtree)

        file_number += 1

    for directive in reversed(deferred):
        # Defer the execution of some directives until the grammar is fully
        # constructed to preserve the order.
        if isinstance(directive, Entry):
            _mark_entry_rule(directive, tree)

        elif isinstance(directive, BackendDef):
            _add_backend_def(generator, directive)

    return tree


def _process(parser: Parser,
             grammar_file: Path,
             lookup_dirs: list[Path],
             backend_name: str,
             generator: CodeGeneratorBase,
             toplevel: bool) -> tuple[list[Include], list[Directive], Grammar]:
    logger.info("file %s", grammar_file)

    with open(grammar_file, 'r', encoding="UTF-8") as fin:
        tree: Grammar = parser.parse(fin)

    includes, deferred = [], []

    for directive in DLL.iter(tree.directives):
        subtree = None
        if isinstance(directive, Include):
            includes.append(directive)

        elif isinstance(directive, Entry):
            deferred.append(directive)
            continue

        elif isinstance(directive, ToplevelQuery):
            if not toplevel:
                continue
            subtree = directive.grammar

        elif isinstance(directive, BackendQuery):
            if backend_name != directive.name.value:
                continue
            subtree = directive.grammar

        elif isinstance(directive, BackendDef):
            # The order of `@include` and `@backend.<directive>` matters:
            # if the include comes first and included file has a definition,
            # then its definition should be inserted first. If the current
            # file has a definition with the same name, its content is
            # appended.
            if includes:
                deferred.append(directive)
                continue
            _add_backend_def(generator, directive)

        elif isinstance(directive, Ignore):
            ids = set(directive.ids)
            for rule in DLL.iter(tree.rules):
                if rule.id in ids:
                    rule.ignore = True

        if subtree:
            tree.merge(subtree)

    return includes, deferred, tree


def _find_include_path(include: Include, lookup_dirs: list[Path]) -> Path:
    path = Path(include.path)
    if not path.exists():
        for dir in lookup_dirs:
            include_path = dir / path
            if include_path.exists():
                logger.info("include found %s", include_path)
                path = include_path
                break
        else:
            msg = (
                f"on {include.filename}: line {include.line}:\n"
                f"include path not found: {include.path!r}"
            )
            raise IncludeNotFound(msg)

    return path


def _mark_entry_rule(entry: Entry, tree: Grammar):
    id = entry.id
    for rule in DLL.iter(tree.rules):
        if rule.id == id:
            rule.entry = True
            return

    msg = (
        f"no rule with the name {entry.id} found in\n"
        f"{entry.filename}: on line {entry.line}"
    )
    raise UnknownEntry(msg)


def _add_backend_def(generator: CodeGeneratorBase, directive: BackendDef):
    with generator.directive(directive.id.value):
        generator.put(reindent(directive.expr, 0))
