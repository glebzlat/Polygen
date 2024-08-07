from __future__ import annotations

from typing import Any, Callable, GenericAlias, Iterable, Optional, Iterator
from collections import ChainMap, defaultdict


class ConfigError(Exception):
    """Exception class for Config related errors."""


class Enum:
    """Variants enumeration.

    Used to define variants for the option.
    """

    def __init__(self, *variants: str | int | bool | None):
        self.variants = variants

    def match(self, value: str | bool) -> bool:
        if isinstance(value, (list, tuple)):
            return all(i in self.variants for i in value)
        else:
            return value in self.variants

    def __repr__(self):
        variants = ', '.join(str(v) for v in self.variants)
        return f"Enum({variants})"

    def __str__(self):
        variants = ' | '.join(str(v) for v in self.variants)
        return f"({variants})"


class Option:
    """Config option.

    Used to define the schema. Immutable.

    Parameters:
        type: Option's type.
        required: If the option is required. If the option is required and
                  not assigned, an error will be raised.
        override: Option can be assigned only once.
        default: Option's default value.
    """

    default: Any
    required: bool
    override: bool
    type: type | GenericAlias | Enum | Config

    def __init__(self,
                 type,
                 default=None,
                 required=False,
                 override=True):
        super().__setattr__('default', default)
        super().__setattr__('required', required)
        super().__setattr__('type', type)
        super().__setattr__('override', override)

    def __eq__(self, other):
        if isinstance(other, Option):
            self_tup = (self.default, self.valid_types)
            other_tup = (other.default, other.valid_types)
            return self_tup == other_tup
        return NotImplemented

    def __hash__(self):
        return hash((self.default, self.valid_types))

    def __setattr__(self, name: str, value: Any):
        raise AttributeError

    def __delattr__(self, name: str, value: Any):
        raise AttributeError

    def __repr__(self):
        if type(self.type) is type:
            tp = self.type.__name__
        elif isinstance(self.type, Enum):
            tp = repr(self.type)
        else:
            tp = self.type
        attrs = ('default', 'required', 'override')
        kwargs = ', '.join(f"{attr}={getattr(self, attr)}" for attr in attrs)
        return f"Option({tp}, {kwargs})"

    def __str__(self):
        return repr(self)


def _convert_bool(types, value: str):
    value = value.lower()
    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        raise ConfigError(f"{value!r} cannot be converted to bool")


class Config:
    def __init__(self,
                 schema: dict[str, Option],
                 unknown_options: str = "ignore"):
        """Initialize Config instance.

        `unknown_options` determines what to do if an option name not in
        configuration schema:

        - "error": raise an error
        - "ignore": silently omit
        - "add": add to config

        By default is is "ignore".

        Args:
            schema: Schema mapping.
            unknown_options: What to do, if option name not in schema.
        """
        self._config = ChainMap(schema)
        self._types: dict[type, tuple[Callable, type | Callable]] = {}

        register = self.register_type
        register(int, int)
        register(bool, _convert_bool)
        register(str, str)

        self._unknown_options: str
        self.unknown_options = unknown_options

    @property
    def schema(self) -> dict[str, Option]:
        """Return the schema mapping."""
        return self._config.maps[-1]

    @property
    def unknown_options(self):
        return self._unknown_options

    @unknown_options.setter
    def unknown_options(self, value):
        allowed_vals = ("error", "ignore", "add")
        if value not in allowed_vals:
            vals = ', '.join(allowed_vals)
            raise ValueError(f"unknown_options must be in {vals}")
        self._unknown_options = value

    def register_type(self,
                      type_: type | GenericAlias,
                      convert_fn: Optional[Callable] = None):
        """Add the new type handler."""
        self._types[type_] = ((lambda types, val: convert_fn(val))
                              if type(convert_fn) is type else convert_fn)

    def override(self, options: dict[str, Any], from_string=False):
        """Assign options to config.

        Each call to `override` adds new option values on the top
        of old values.

        `from_string` is used when the option dictionary is created
        from string representation, and its values are strings. Config
        will convert strings to option values.

        Args:
            options: Option dictionary.
            from_string: Convert string values to types.

        Raises:
            ConfigError
        """
        self._try_insert_map(self._override, options, from_string)

    def parse(self, it: Iterable[str]):
        """Parse and override options.

        Option string has the format `<option_name>.<attribute>=<value>`,
        where `.<attribute>` is optional: `<option_name>=<value>`.

        The first option form can be used with options of type `dict` only.

        Args:
            it: Iterable of strings.

        Raises:
            ConfigError
        """
        self._try_insert_map(self._parse, it)

    def validate(self) -> None:
        """Validate added options.

        During the validation, options that are required but not percieved
        in the config are found. If there are such options, ConfigError
        will be raised.

        Raises:
            ConfigError.
        """
        required_options: list[str] = []
        for name, value in self._config.items():
            if isinstance(value, Option) and value.required:
                required_options.append(name)
            elif isinstance(value, Config):
                value.validate()

        if required_options:
            opts = ', '.join(repr(n) for n in required_options)
            msg = f"required options: {opts}"
            raise ConfigError(msg)

    def _try_insert_map(self, fn: Callable, *args: Any):
        self._config.maps.insert(0, {})
        try:
            fn(*args)
        except Exception:
            self._config.maps.pop(0)
            raise

    def _override(self, options: dict[str, Any], convert=False):
        schema = self.schema

        def _convert_value(name, val, msg=None):
            fn = self._types.get(option.type)
            if not fn:
                msg = msg or f"{name!r}: cannot convert: {val!r}"
                raise ConfigError(msg)

            try:
                return fn(self._types, value)
            except Exception as e:
                raise ConfigError(f"option {name!r}: {e}")

        for name, value in options.items():
            if name not in schema:
                if self.unknown_options == "error":
                    msg = f"cannot add name {name!r} that is not in config"
                    raise ConfigError(msg)
                elif self.unknown_options == "ignore":
                    pass
                elif self.unknown_options == "add":
                    self._config[name] = value
                continue

            option = self._get_option(name)

            if isinstance(option.type, Config):
                self._config[name] = cfg = option.type.copy()
                cfg.override(value, convert)
                continue

            if convert:
                value = _convert_value(name, value)
            else:
                success, msg = self._valid_value(name, value, option)
                if not success:
                    value = _convert_value(name, value)

            self._config[name] = value

    def _valid_value(self, name, value, option) -> tuple[bool, str | None]:
        tp = option.type

        if isinstance(tp, GenericAlias):
            origin, args = tp.__origin__, tp.__args__
            if not isinstance(value, origin):
                msg = f"option {name!r} must be of type {tp}, got {type(value)}"
                return False, msg

            if issubclass(origin, dict) and len(args) == 2:
                val_type = args[1]
                for attr, val in value.items():
                    if not isinstance(val, val_type):
                        msg = (f"option {name!r}: {attr!r} must be of type "
                               f"{val_type}, got {type(val)}: {val!r}")
                        return False, msg

            elif issubclass(origin, (list, tuple)) and args:
                val_type = args[0]
                for i, val in enumerate(value):
                    if not isinstance(val, val_type):
                        msg = (
                            f"option {name!r}: element with index {i} must "
                            f"be of type {val_type}, got {type(val)}: {val!r}")
                        return False, msg

        elif type(tp) is type and not isinstance(value, tp):
            msg = (f"option {name!r} must be of type {tp}, got {type(value)}: "
                   f"{value!r}")
            return False, msg

        elif isinstance(tp, Enum) and not tp.match(value):
            msg = (f"option {name!r} must be one of the following: {tp}, "
                   f"got {value!r}")
            return False, msg

        return True, None

    def _parse(self, it: Iterable[str]):
        dct: defaultdict[dict] = defaultdict(dict)

        for s in it:
            lhs, value = s.split('=')

            if '.' in lhs:
                name, attr = lhs.split('.', 1)
                dct[name][attr] = value
            else:
                dct[lhs] = value

        self._override(dct, convert=True)

    def _get_option(self, name: str):
        if name not in self.schema:
            raise ConfigError
        option = self.schema[name]
        if len(self._config.maps) > 2 and not option.override:
            msg = f"option {name!r} can be assigned only once"
            raise ConfigError(msg)
        return self.schema[name]

    def items(self) -> Iterator[tuple[str, Any]]:
        for name, value in self._config.items():
            if isinstance(value, Option):
                value = value.default
            yield name, value

    def keys(self) -> Iterator[str]:
        yield from self

    def values(self) -> Iterator[Any]:
        for val in self._config.values():
            if isinstance(val, Option):
                val = val.default
            yield val

    def clear(self):
        """Remove assigned options, preserving the schema.

        After calling this method, `Config.layers` returns 0.
        """
        self._config.maps = self._config.maps[-1:]

    @property
    def layers(self) -> int:
        """Total number of override layers."""
        return len(self._config.maps) - 1

    def pop_layer(self) -> Optional[dict[str, Any]]:
        """Remove the latest override layer, if exists.

        Removes and returns the latest added override layer, if exists.
        Otherwise, does nothing and returns None.
        """
        if len(self._config.maps) == 1:
            return None
        return self._config.maps.pop(0)

    def __getattr__(self, name: str) -> Any:
        if name in self._config:
            value = self._config[name]
            if isinstance(value, Option):
                return value.default
            return value

        raise AttributeError(f"no such config value: {name!r}")

    def copy(self, *, with_options=False) -> Config:
        """Create a copy of Config object.

        Kwargs:
            with_options: Controls whether to copy the original object's
                          options or not.
        """
        obj = Config(self.schema)
        obj.unknown_options = self.unknown_options

        if with_options:
            for map in self._config.maps[-2::-1]:
                obj.override(map)
                obj.validate()

        return obj

    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any):
        setattr(self, name, value)

    def __delitem__(self, name: str):
        delattr(self, name)

    def __contains__(self, name: str) -> bool:
        return name in self._config

    def __iter__(self) -> Iterator[str]:
        yield from self._config

    def __repr__(self):
        lines = ["Config({"]
        for name, val in self.schema.items():
            lines.append(f"  {name!r}: {val!r},")
        lines.append("})")
        return '\n'.join(lines)

    def __str__(self):
        return repr(self)
