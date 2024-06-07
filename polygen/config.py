import sys

from os import PathLike, path
from typing import Any
from pathlib import Path
from collections import ChainMap

FS_ENCODING = sys.getfilesystemencoding() or sys.getdefaultencoding()
CONFIG_FILENAME = "config.py"


class ConfigError(Exception):
    pass


class _Enum:
    def __init__(self, *variants: str | bool | None):
        self.variants

    def match(self, value: str | bool | None) -> bool:
        if isinstance(value, (list, tuple)):
            return all(i in self.variants for i in value)
        else:
            return value in self.variants


class _Opt:

    default: Any
    required: bool
    override: bool
    valid_types: type | tuple[type, ...] | tuple[()] | _Enum

    def __init__(self,
                 valid_types,
                 default=None,
                 required=False,
                 override=True):
        super().__setattr__('default', default)
        super().__setattr__('required', required)
        super().__setattr__('valid_types', valid_types)
        super().__setattr__('override', override)
        super().__setattr__('_reserved',
                            {'default', 'valid_types', 'required', 'override'})

    def __eq__(self, other):
        if isinstance(other, _Opt):
            self_tup = (self.default, self.valid_types)
            other_tup = (other.default, other.valid_types)
            return self_tup == other_tup
        return NotImplemented

    def __hash__(self):
        return hash((self.default, self.valid_types))

    def __setattr__(self, name: str, value: Any):
        if name in self._reserved:
            raise TypeError
        super().__setattr__(name, value)

    def __delattr__(self, name: str, value: Any):
        if name in self._reserved:
            raise TypeError
        delattr(super(), name, value)


class Config:

    # This code is heavily inspired by Sphinx:
    # https://github.com/sphinx-doc/sphinx/blob/master/sphinx/config.py

    config_values = {
        'name': _Opt(str, required=True),
        'language': _Opt(str, required=True),
        'version': _Opt(str, default='0'),
        'datetime_fmt': _Opt(str, default='%Y-%m-%dT%H:%M'),
        'capabilities': _Opt(list, default=[]),
        'files': _Opt(dict, default={}),
        'definitions': _Opt(dict, default={}),
        'generator': _Opt((str, Path), default='gen.py', override=False),
        'parser_name': _Opt(str, default='Parser'),
        'options': _Opt(dict, default={}, override=False)
    }

    def __init__(self,
                 config: dict[str, Any],
                 overrides: dict[str, Any] | None = None):
        """Create Config object.

        Args:
            config: Primary config options from the config file.
            overrides: Optional primary config options overrides.
        """
        self._config = ChainMap(
            {}, config, Config.config_values.copy())
        if overrides is not None:
            self.overrides(overrides)

    def overrides(self, overrides: dict[str, Any]):
        """Override options."""
        overrides = overrides.copy()
        for name, value in overrides.items():

            # Override a dictionary key.
            if '.' in name:
                attr, key = name.split('.', 1)

                if attr not in self._config:
                    msg = f"option not in config: {attr}"
                    raise ConfigError(msg)

                option = self._config[attr]
                if type(option) is _Opt:
                    if not option.override:
                        msg = f"option not overridable: {attr}"
                        raise ConfigError(msg)
                    self._config[attr] = option = option.default

                if type(option) is dict:
                    option[key] = value
                else:
                    msg = f"cannot override key {key}: {attr} is not a dict"
                    raise ConfigError(msg)

            # Override option.
            else:
                if name not in self._config:
                    msg = f"option not in config: {name}"
                    raise ConfigError(msg)

                value = self.convert_overrides(name, value)
                self._config[name] = value

    @classmethod
    def read(cls,
             config_dir: str | PathLike[str],
             overrides: dict | None = None):
        """Create the Config object from configuration file."""
        filename = path.join(config_dir, CONFIG_FILENAME)
        if not path.isfile(filename):
            raise ConfigError()
        namespace = eval_config_file(filename)

        obj = cls(namespace)
        if overrides is not None:
            obj.overrides(overrides)
        return obj

    def convert_overrides(self, name: str, value: str) -> Any:
        """Infer the option's type and convert the value."""

        # Ensure to take the _Opt object from the config.
        opt = self._config.maps[-1][name]
        default = opt.default
        valid_types = opt.valid_types

        if opt.required or not opt.override:
            msg = f"cannot override required option: {name}"
            raise ConfigError(msg)

        if valid_types == Any:
            return value
        elif type(default) is bool:
            if value in {'1', 'true', 'True'}:
                return True
            elif value in {'0', 'false', 'False'}:
                return False
            else:
                msg = f"incorrect value for bool option {name}: {value}"
                raise ValueError(msg)
        elif isinstance(default, dict):
            msg = (f"cannot override dictionary config setting {name} "
                   f"(use '{name}.key=value')")
            raise ValueError(msg)
        elif isinstance(default, list):
            return value.split(',')
        elif isinstance(default, int):
            try:
                return int(value)
            except ValueError as e:
                raise ValueError from e
        else:
            return value

    def __getattr__(self, name: str) -> Any:
        if name in self._config:
            value = self._config[name]
            if type(value) is _Opt:
                return value.default
            return value

        if name.startswith('_'):
            type_name = type(self).__name__
            msg = f"{type_name!r} object has no attribute {name!r}"
            raise AttributeError(msg)

        raise AttributeError(f"no such config value: {name!r}")

    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)

    def __setitem__(self, name: str, value, Any):
        setattr(self, name, value)

    def __delitem__(self, name: str):
        delattr(self, name)

    def __contains__(self, name: str) -> bool:
        return name in self._config


def eval_config_file(filename: str | PathLike[str]) -> dict[str, Any]:
    namespace = {}

    try:
        with open(filename, 'rb') as fin:
            code = compile(fin.read(), filename.encode(FS_ENCODING), 'exec')
            exec(code, namespace)
    except SyntaxError as e:
        raise ConfigError(f'syntax error in the config file: {e}') from e
    except SystemExit as e:
        raise ConfigError('the configuration file called sys.exit()') from e
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f'an exception in the config file: {e}') from e

    return namespace
