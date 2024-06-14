from typing import Iterable
from os import PathLike
from pathlib import Path
from io import StringIO
from datetime import datetime
from enum import StrEnum
from io import TextIOBase

from .__version__ import __version__
from .config import Config

from .tree_modifier.tree_modifier import (
    MODIFIERS,
    TreeModifier
)
from .tree_modifier.errors import TreeModifierWarning

from .parser import Parser as GrammarParser
from .preprocessor import FilePreprocessor

MODULE_PATH = Path(__file__).parent.absolute()
CODEGEN_PATH = MODULE_PATH.parent / 'codegen'
BACKEND_DIRS = list(CODEGEN_PATH.iterdir())


class PredefinedDirectives(StrEnum):
    """Predefined Preprocessor directives."""

    HEADER = "header"
    FOOTER = "footer"
    PARSER_NAME = "parser_name"
    DATETIME = "datetime"
    BODY = "body"
    ENTRY = "entry"
    VERSION = "version"


class GeneratorError(Exception):
    """Exceptions related to the Generator."""


class Generator:
    """Backends manager.

    Each backend minimally consists of a config file, a generator and a
    skeleton file.

    A config file defines generator capabilities (which nodes and language
    constructions it accepts), preprocessor definitions and a list of files
    to be preprocessed and converted into the ready to use parser

    The generator is a Python module, which takes the grammar tree and
    produces the main code of the parser.

    The skeleton file is the rest of the code of the parser and utility code.
    It contains directives that will be substituted by the preprocessor, along
    with the code.

    Generator manages backend configurations, setups modifiers accordingly
    to backend's capabilities, fires up the grammar parser, producing the
    grammar, uses the TreeModifier to rewrite the grammar, uses the backend
    generator to create the prepared code and then fires up file preprocessor
    to insert this code into the skeleton, thus creating a final file.
    """

    def __init__(self, backends: dict[str, Config]):
        """Create Generator instance.

        Args:
            backends: A dictionary BackendName -> Config.
        """
        self._backends = backends
        self._modifier_warning = None

    @classmethod
    def setup(cls, directories: Iterable[str | PathLike[str]] | None = None):
        """Create a generator from a sequence of backend directories.

        Args:
            directories: A sequence of directories containing config files.
                If not given, then default codegen directories will be taken.

        Returns:
            An instance of Generator.
        """
        if directories is None:
            directories = BACKEND_DIRS
        paths = (Path(d) for d in directories)

        backends = {}
        for path in paths:
            if not path.exists():
                continue
            config = Config.read(path)
            config.backend_path = path
            backends[config.name] = config

        return Generator(backends)

    def backends_info(self) -> dict[str, tuple[str, str]]:
        """Get the info about backends.

        Returns:
            A dictionary BackendName -> tuple of Language and Version.
        """
        return {name: (conf.language, conf.version)
                for name, conf in self._backends.items()}

    def generate(self,
                 backend: str,
                 output_dir: str | PathLike[str],
                 *,
                 options: dict,
                 grammar_file: str | PathLike[str] | None = None,
                 grammar: str | TextIOBase | None = None):
        """Produce the output.

        If `grammar_file` nor `grammar` argument is not set, or they're both
        set, ValueError exception will be raised.

        Args:
            backend: Backend name. Must be in available backends, which can
                be seen via `Generator.backends_info` method.
            output_dir: Output directory. The directory must be present in
                the filesystem.

        Kwargs:
            options: A dictionary of overrides.
            grammar_file: Path to a grammar file.
            grammar: A string or a stream of the grammar.

        Raises:
            GeneratorError.
            TreeModifierWarning.
            ValueError.
        """
        if backend not in self._backends:
            msg = f"no such backend: {backend!r}"
            raise GeneratorError(msg)

        if (grammar is None and grammar_file is None
                or grammar is not None and grammar_file is not None):
            raise ValueError("give either a grammar or a grammar_file")

        if grammar_file is not None:
            with open(grammar_file, 'rt', encoding='UTF-8') as fin:
                self._generate(backend, output_dir, options, fin)
        elif grammar is not None:
            self._generate(backend, output_dir, options, grammar)

    def _generate(self,
                  backend: str,
                  output_dir: str | PathLike[str],
                  options,
                  grammar):
        config = self._backends[backend]
        config.overrides(options)

        parser = GrammarParser(grammar)
        grammar = parser.parse()
        if grammar is None:
            raise GeneratorError("parser failure")
        grammar = grammar.value

        # print(repr(grammar))
        modifiers = self._init_modifiers(config)
        visitor = TreeModifier(modifiers)
        try:
            visitor.apply(grammar)
        except TreeModifierWarning as warn:
            self._modifier_warning = warn
        # print(repr(grammar))

        stream = StringIO()
        gen_cls = self._get_gen(config)
        gen = gen_cls(grammar=grammar, stream=stream, config=config)
        gen.generate()
        stream.seek(0)

        pre = PredefinedDirectives
        for dir in config.definitions:
            if dir in pre.__members__:
                msg = f"config hinders predefined directive: {dir}"
                raise GeneratorError(msg)

        directives = {
            pre.PARSER_NAME: config.parser_name,
            pre.DATETIME: datetime.today().strftime(config.datetime_fmt),
            pre.BODY: stream.read(),
            pre.ENTRY: grammar.entry.id.value,
            pre.VERSION: __version__,

            **config.definitions
        }

        proc = FilePreprocessor(directives)

        files = {}
        backend_root: Path = config.backend_path

        output_dir = Path(output_dir)
        if not output_dir.exists():
            msg = f"output directory {output_dir} does not exist"
            raise GeneratorError(msg)
        if not output_dir.absolute():
            output_dir = Path.cwd() / output_dir

        for skel_file, output_file in config.files.items():
            # If the output file path is not absolute, it is treated as
            # relative to the directory where Polygen was started
            output_file = output_dir / output_file
            skel_file = backend_root / skel_file

            if not skel_file.exists() or not skel_file.is_file():
                msg = f"{skel_file!s} does not exist or not a file"
                raise GeneratorError(msg)

            files[skel_file] = output_file

        proc.process(files)

        if self._modifier_warning is not None:
            raise self._modifier_warning

    def _init_modifiers(self, config: Config):
        modifiers = [(mod() if type(mod) is type else mod) for mod in MODIFIERS]
        return modifiers

    def _get_gen(self, config: Config):
        backend_root = config.backend_path
        module: Path = backend_root / config.generator
        if not module.exists():
            msg = f"{module} generator file does not exist"
            raise GeneratorError(msg)

        namespace = {}
        with open(module, 'rb') as fin:
            code = compile(fin.read(), fin.name, 'exec')
            exec(code, namespace)

        return namespace['Generator']
