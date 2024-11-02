from abc import abstractmethod
from typing import Optional, Any
from pathlib import Path

from polygen.node import Grammar


class TranslationError(Exception):
    """Base class for errors raised by passes

    Translation errors raised in conditions when the translation should not
    be continued. Errors can be of two levels of severity: critical and non
    critical. Critical error halts the execution right in the moment it is
    registered. Non-critical error allows the pass to end normally, and then
    the translation stops.
    """

    critical: bool

    def __init__(self, message: str, *args: Any, **kwargs: Any):
        super().__init__(*args)
        self.message = message
        self.kwargs = kwargs

    def __str__(self):
        return self.message.format(*self.args, **self.kwargs)


class TranslationWarning(Warning):
    """Base class for warnings raised by passes

    Warnings don't halt the translation process. They are collected along
    all passes and then should be printed in batch.
    """

    def __init__(self, message: str, *args: Any, **kwargs: Any):
        super().__init__(*args)
        self.message = message
        self.kwargs = kwargs

    def __str__(self):
        return self.message.format(*self.args, **self.kwargs)


class Context:
    """Translation context

    Context does several things: it is responsible for error and warning
    registering, it carries the neccessary information along the translation
    process, and it can be used to pass custom parameters from one translator
    to the subsequent translators.
    """

    def __init__(self):
        self.errors: list[TranslationError] = []
        self.warnings: list[TranslationWarning] = []

        self.backend_name: Optional[str] = None

        self.include_paths: Optional[list[Path]] = None
        self.grammar_source: Optional[Path] = None
        self.source_files: list[Path] = []
        self.directives: dict[str, str] = {}

        self.grammar: Optional[Grammar] = None
        self.reserved_words: Optional[set[str]] = None

        self.namespace: dict[str, Any] = {}

    def error(self, err: TranslationError):
        """Register an error

        Halts the translation if error is critical.
        """
        self.errors.append(err)
        if err.critical:
            raise err

    def warning(self, warn: TranslationWarning):
        """Register a warning"""
        self.warnings.append(warn)

    def clear(self):
        """Clear namespace"""
        self.namespace.clear()

    def __getitem__(self, key: str) -> Any:
        return self.namespace[key]

    def __setitem__(self, key: str, value: Any):
        self.namespace[key] = value

    def __contains__(self, key: str):
        return self.namespace.__contains__(key)


class Translator:
    """Base translator

    Classes that inherit from Translator are translation passes that modify
    the grammar tree.

    Translators should not use any exceptions and warnings except inherited
    from TranslationError and TranslationWarning in cases related to the
    grammar tree. They should not raise errors and warnings directly, instead
    registering them in the context.
    """

    @abstractmethod
    def translate(self, ctx: Context):
        ...
