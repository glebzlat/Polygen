from __future__ import annotations

from typing import Any, Callable, Optional, Iterable

from ..config import Config, Option

from .modifiers import (
    CheckUndefinedRules,
    CheckRedefinedRules,
    ReplaceNestedExprs,
    FindEntryRule,
    CreateAnyChar,
    IgnoreRules,
    GenerateMetanames,
    AssignMetaRules,
    ValidateNodes
)
from .leftrec import compute_lr


class RegistryError(Exception):
    pass


class ModifierRegistry:

    schema_skeleton = {
        "_enabled": Option(bool, default=True)
    }

    def __init__(self):
        self._modifiers: dict[str, tuple[type, Config]] = {}

        add = self.add_modifier

        add("find-entry", FindEntryRule)
        add("validate-rules", ValidateNodes)
        add("any-char", CreateAnyChar,
            {"strict": Option(bool, default=False)})
        add("replace-exprs", ReplaceNestedExprs)
        add("undef-rules", CheckRedefinedRules)
        add("redef-rules", CheckUndefinedRules)
        add("meta-rules", AssignMetaRules)
        add("ignore-rules", IgnoreRules)
        add("generate-meta", GenerateMetanames)
        add("compute-lr", compute_lr)

    def add_modifier(self,
                     name: str,
                     cls: type | Callable,
                     options: Optional[dict[str, Option]] = None):
        if name in self._modifiers:
            raise ValueError(f"duplicate modifier name: {name}")

        schema = self.schema_skeleton.copy()
        if type(cls) is type:

            if options is None:
                options = {}

            for key, opt in options.items():
                if key in schema:
                    raise ValueError()
                schema[key] = opt

        else:
            # It is callable, so it cannot be instantiated and thus
            # can not take any options.
            if options is not None:
                raise ValueError(f"cannot use options with callable: {name}")

        self._modifiers[name] = cls, Config(schema=schema,
                                            unknown_options="error")

    @property
    def schema(self) -> dict[str, Config]:
        opts = {}
        for name, (cls, cfg) in self._modifiers.items():
            opts[name] = cfg
        return opts

    def configure(self, options: dict[str, dict[str, Any]]) -> list[object]:
        options = options.copy()
        mods = []

        for name in self._modifiers:
            cls, config = self._modifiers[name]

            config = config.copy()
            if name in options:
                config.override(options.pop(name), from_string=True)
            # print(f"{cls.__name__}: {config._enabled}")
            if not config._enabled:
                continue

            if type(cls) is not type:
                mods.append(cls)
                continue

            public_options = {name: val for name, val in config.items()
                              if not name.startswith('_')}
            mods.append(cls(**public_options))

        if options:
            keys = ', '.join(repr(s) for s in options)
            raise RegistryError(f"{keys} not in modifiers")

        return mods

    @classmethod
    def parse_modifier_options(
            cls, options: Iterable[str]) -> dict[str, str | bool]:
        opts = {}
        for s in options:
            lhs, value = s.split('=', 1)
            prefix, *key = lhs.split('.')

            if prefix != "mod":
                continue

            if not key:
                raise RegistryError(f"key expected: {s!r}")

            if len(key) == 1:
                opts.setdefault(key[0], {})['_enabled'] = value
            else:
                level, last_idx = opts, len(key) - 1
                for i, k in enumerate(key):
                    if i == last_idx:
                        level[k] = value
                    else:
                        level = level.setdefault(k, {})

        return opts
