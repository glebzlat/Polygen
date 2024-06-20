from __future__ import annotations

from collections import defaultdict
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

        self._modifiers[name] = cls, Config(schema=schema)

    @property
    def schema(self) -> dict[str, dict[str, Option]]:
        opts = {}
        for name, (cls, options) in self._modifiers.items():
            opts[name] = options
        return opts

    def configure_modifier(self,
                           name: str,
                           options: Optional[dict[str, Any]]) -> object | None:
        if name not in self._modifiers:
            raise ValueError()

        cls, config = self._modifiers[name]

        config = config.copy()
        if options is not None:
            config.override(options)
        # print(f"{cls.__name__}: {config._enabled}")
        if not config._enabled:
            return None

        if type(cls) is not type:
            return cls

        public_options = {name: val for name, val in config.items()
                          if not name.startswith('_')}
        return cls(**public_options)

    def configure(self, options: dict[str, dict[str, Any]]) -> list[object]:
        modifiers = self._modifiers
        mods = (self.configure_modifier(n, options.get(n)) for n in modifiers)
        return [m for m in mods if m is not None]


def parse_modifier_options(registry: ModifierRegistry,
                           options: Iterable[str]):
    opts = defaultdict(dict)
    for s in options:
        lhs, value = s.split('=', 1)
        key, *subkey = lhs.split('.')

        if len(subkey) == 1:
            opts[key][subkey[0]] = value
        elif len(subkey) > 1:
            raise ValueError
        else:
            opts[key]['_enabled'] = value == 'True'

    # print(opts)
    return registry.configure(opts)
