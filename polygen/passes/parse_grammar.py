import logging
import traceback

from pathlib import Path
from collections import deque
from io import StringIO

from polygen.translator import Translator, Context, TranslationError
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


logger = logging.getLogger("polygen.passes.parse_grammar")


class CircularIncludeError(TranslationError):
    critical = True


class IncludeNotFound(TranslationError):
    critical = True


class UnknownEntry(TranslationError):
    critical = True


class ParserError(TranslationError):
    critical = True

    def __init__(self, error: Exception):
        super().__init__(
            ''.join(traceback.format_exception(SyntaxError, error, None)))
        self.error = error


class ParseGrammar(Translator):

    def translate(self, ctx: Context):
        toplevel_include = Include(str(ctx.grammar_source), 0, "<preprocessor>")
        queue = deque([toplevel_include])
        tree = None

        reader = Reader(None)
        parser = Parser(reader)

        file_number = 0
        included = set()
        deferred = []

        while queue:
            include = queue.popleft()
            if include in included:
                # Prevent files that were already included by another branch
                # from being included
                continue
            file = self.find_include_path(ctx, include)

            includes, df, subtree = self._process(
                ctx,
                parser,
                file,
                ctx.backend_name,
                file_number == 0
            )
            deferred.extend(df)

            included.add(include)
            for i in includes:
                if i == include or i in queue:
                    err = CircularIncludeError(
                        f"circular include in {i.filename}:\n"
                        f"line: {i.line}: {i.path}"
                    )
                    ctx.error(err)
                queue.append(i)

            if not tree:
                tree = subtree
            elif tree is not subtree:
                tree.merge(subtree)

            file_number += 1

        for directive in reversed(deferred):
            # Defer the execution of some directives until the grammar is fully
            # constructed

            if isinstance(directive, Entry):
                self.mark_entry_rule(ctx, directive, tree)

            elif isinstance(directive, BackendDef):
                self.add_backend_def(ctx, directive)

            elif isinstance(directive, Ignore):
                ids = set(directive.ids)
                for rule in DLL.iter(tree.rules):
                    if rule.id in ids:
                        rule.ignore = True

        ctx.grammar = tree

    def _process(
        self,
        ctx: Context,
        parser: Parser,
        source_file: Path,
        backend_name: str,
        toplevel: bool
    ) -> tuple[list[Include], list[Directive], Grammar]:
        logger.info("file %s", source_file)
        ctx.source_files.append(source_file)

        with open(source_file, 'r', encoding="UTF-8") as fin:
            try:
                tree: Grammar = parser.parse(fin)
            except SyntaxError as e:
                ctx.error(ParserError(e))

        includes, deferred = [], []

        for directive in DLL.iter(tree.directives):
            subtree = None

            if isinstance(directive, Include):
                includes.append(directive)

            elif isinstance(directive, Entry):
                deferred.append(directive)
                continue

            elif isinstance(directive, ToplevelQuery):
                if toplevel:
                    subtree = directive.grammar

            elif isinstance(directive, BackendQuery):
                if backend_name == directive.name.value:
                    subtree = directive.grammar

            elif isinstance(directive, BackendDef):
                if includes:
                    deferred.append(directive)
                    continue
                self.add_backend_def(ctx, directive)

            elif isinstance(directive, Ignore):
                deferred.append(directive)

            if subtree:
                tree.merge(subtree)

        return includes, deferred, tree

    def find_include_path(
        self,
        ctx: Context,
        include: Include,
    ) -> Path:
        path = Path(include.path)
        if path.exists():
            return path

        # Not a relative include
        for dir in ctx.include_paths:
            include_path = dir / path
            if include_path.exists():
                logger.info("include found %s", include_path)
                return include_path

        err = IncludeNotFound(
            f"in {include.filename}: line {include.line}:\n"
            f"include not found: {include.path!r}"
        )
        ctx.error(err)

    def mark_entry_rule(self, ctx: Context, entry: Entry, tree: Grammar):
        id = entry.id
        for rule in DLL.iter(tree.rules):
            if rule.id == id:
                rule.entry = True
                return

        err = UnknownEntry(
            f"entry rule {entry.id} not found: in {entry.filename} "
            f"on line {entry.line}"
        )
        ctx.error(err)

    def add_backend_def(self, ctx: Context, directive: BackendDef):
        key, val = directive.id.value, directive.expr
        print(f"{val}\n", file=ctx.directives.setdefault(key, StringIO()))
