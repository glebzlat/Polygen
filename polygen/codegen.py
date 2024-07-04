from typing import Iterable
from os import PathLike
from pathlib import Path
from io import StringIO
from datetime import datetime
from enum import StrEnum
from io import TextIOBase

from .__version__ import __version__
from .config import Config, Option, read_file

from .modifier.tree_modifier import TreeModifier
from .modifier.errors import TreeModifierWarning
from .modifier.registry import ModifierRegistry

from .reader import Reader
from .parser import Parser as GrammarParser
from .preprocessor import FilePreprocessor

MODULE_PATH = Path(__file__).parent.absolute()
CODEGEN_PATH = MODULE_PATH / 'backend'
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


class CodeGeneratorError(Exception):
    """CodeGenerator errors occured due to the user's mistakes.

    Instances of this class contain descriptive messages and should be
    given to the user without traceback."""


class CodeGenerator:
    """Handles backend managing and code generation.

    Code generation process consists of following stages:
        1. Backend configuration selection.
        2. Parser converts text grammar representation into grammar tree.
        3. `ModifierRegistry` creates and configures modifier instances,
           according to the backend modifier's configuration and options
           overrides given by the user.
        4. `TreeModifier` uses created modifiers to make the grammar tree.
        5. Code generator takes modified grammar tree and converts it
           into the code.
        6. Preprocessor takes skeleton file from config, the code from
           the previous stage, user defined options and inserts the code
           into the skeleton file, creating valid source code.

    Thus, `CodeGenerator` is responsible for:
        1. Backend configurations managing.
        2. Creation and managing of Parser, Registry, Modifier and
           Preprocessor instances.

    Each backend is defined by its config file. Also backends must have
    the code generator and at least one skeleton file.
    """

    config_values = {
        'name': Option(str, required=True),
        'language': Option(str, required=True),
        'version': Option(str, default='0'),
        'datetime_fmt': Option(str, default='%Y-%m-%dT%H:%M'),
        'files': Option(dict, default={}),
        'definitions': Option(dict, default={}),
        'generator': Option((str, Path), default='gen.py', override=False),
        'parser_name': Option(str, default='Parser'),
        'options': Option(dict, default={}, override=False)
    }

    def __init__(self, backends: dict[str, Config]):
        """Create CodeGenerator instance.

        Args:
            backends: A dictionary BackendName -> Config.
        """
        self._backends: dict[str, Config] = backends

        self.registry = ModifierRegistry()

        self._modifier_warning = None

    def add_backend(self, name: str, config: Config):
        """Add backend config."""
        if name in self._backends:
            raise ValueError(f"duplicate backend name: {name}")
        self._backends[name] = config

    def add_backend_dir(self, directory: str | PathLike[str]):
        """Add backend config from directory."""
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"path does not exist or not a directory: {path}")

        config = Config.read(path)
        config.backend_path = path
        self.add_backend(config.name, config)

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
            filename = path / "config.py"
            cfg = read_file(cls.config_values, filename)
            cfg.backend_path = path
            backends[cfg.name] = cfg

        return CodeGenerator(backends)

    def backends_info(self) -> dict[str, tuple[str, str]]:
        """Get the info about backends.

        Returns:
            dict[Backend name, tuple[Language, Version]]
        """
        return {name: (conf.language, conf.version)
                for name, conf in self._backends.items()}

    def generate(self,
                 backend: str,
                 output_dir: str | PathLike[str],
                 *,
                 modifier_options: dict,
                 grammar_file: str | PathLike[str] | None = None,
                 grammar: str | TextIOBase | None = None):
        """Produce the output.

        If the `grammar` argument is given, then will Parser will read it.
        If the `grammar_file` argument is given, then the corresponding
        file will be opened and Parser will read data from it.
        If both arguments are given or they are both None, ValueError will
        be raised

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

        exc = ValueError("give either a grammar or a grammar_file")

        if grammar is not None and grammar_file is not None:
            raise exc
        elif grammar_file is not None:
            istream = open(grammar_file, 'rt', encoding='UTF-8')
        elif grammar is not None:
            istream = grammar
        else:
            raise exc

        try:
            self._generate(backend, output_dir, modifier_options, istream)
        finally:
            if isinstance(istream, TextIOBase):
                istream.close()

    def get_grammar_tree(self,
                         input_data: str | TextIOBase,
                         modifier_options
                         ):
        """Generate the grammar from the input data.

        Grammar tree generation happens in two stages:
            1. Parser generates raw grammar tree.
            2. Tree modifier adds, removes and modifies nodes in the grammar,
               making it suitable for parser generator.

        Stage 2 consists of two substages:
            2.1. Creation of modifier instances through the Modifier registry,
                 which performs modifier instances setup.
            2.2. Applying the created modifies on the raw grammar tree
                 using TreeModifier.

        Args:
            options: Options for ModifierRegistry.
            input_data: Parser input data.

        Return:
            Grammar instance.

        Raises:
            GeneratorError
        """

        reader = Reader(input_data)
        parser = GrammarParser(reader)
        grammar = parser.parse()
        if grammar is None:
            raise CodeGeneratorError("parser failure")
        grammar = grammar.value

        modifiers = self.registry.configure(modifier_options)

        visitor = TreeModifier(modifiers)
        try:
            visitor.apply(grammar)
        except TreeModifierWarning as warn:
            self._modifier_warning = warn

        return grammar

    def _generate(self,
                  backend: str,
                  output_dir: str | PathLike[str],
                  modifier_options,
                  grammar):
        grammar = self.get_grammar_tree(grammar, modifier_options)
        config = self._backends[backend]

        stream = StringIO()
        gen_cls = self._get_gen(config)
        gen = gen_cls(grammar=grammar, stream=stream, config=config)
        gen.generate()
        stream.seek(0)

        pre = PredefinedDirectives
        for dir in config.definitions:
            if dir in pre.__members__:
                msg = f"config hinders predefined directive: {dir}"
                raise CodeGeneratorError(msg)

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
            raise CodeGeneratorError(msg)
        if not output_dir.absolute():
            output_dir = Path.cwd() / output_dir

        for skel_file, output_file in config.files.items():
            # If the output file path is not absolute, it is treated as
            # relative to the directory where Polygen was started
            output_file = output_dir / output_file
            skel_file = backend_root / skel_file

            if not skel_file.exists() or not skel_file.is_file():
                msg = f"{skel_file!s} does not exist or not a file"
                raise CodeGeneratorError(msg)

            files[skel_file] = output_file

        proc.process(files)

        if self._modifier_warning is not None:
            raise self._modifier_warning

    def _get_gen(self, config: Config):
        backend_root = config.backend_path
        module: Path = backend_root / config.generator
        if not module.exists():
            msg = f"{module} generator file does not exist"
            raise ValueError(msg)

        namespace = {}
        with open(module, 'rb') as fin:
            code = compile(fin.read(), fin.name, 'exec')
            exec(code, namespace)

        return namespace['Generator']
