import unittest

from polygen.generator.config import Config, Option, Enum, ConfigError


class TestOption(unittest.TestCase):

    def test_mutability(self):
        opt = Option(int)

        with self.assertRaises(AttributeError):
            opt.type = float

        with self.assertRaises(AttributeError):
            opt.default = 42


class TestConfig(unittest.TestCase):

    def test_int_option(self):
        schema = {"int": Option(int)}
        cfg = Config(schema)

        cfg.override({"int": 42})
        cfg.validate()

        self.assertEqual(cfg["int"], 42)
        self.assertEqual(cfg.int, 42)

    def test_parse_int_option(self):
        schema = {"int": Option(int)}
        cfg = Config(schema)

        cfg.parse(["int=42"])
        cfg.validate()

        self.assertEqual(cfg.int, 42)

    def test_option_default(self):
        schema = {"bool": Option(bool, default=True)}
        cfg = Config(schema)

        self.assertEqual(cfg.bool, True)

        cfg.override({"bool": False})
        cfg.validate()

        self.assertEqual(cfg.bool, False)

    def test_parse_bool_option(self):
        schema = {"bool": Option(bool)}
        cfg = Config(schema)

        cfg.parse(["bool=True"])
        cfg.validate()

        self.assertEqual(cfg.bool, True)

        cfg.clear()
        cfg.parse(["bool=false"])
        cfg.validate()

        self.assertEqual(cfg.bool, False)

        cfg.clear()
        with self.assertRaises(ConfigError):
            cfg.parse(["bool=hello"])

    def test_parse_string_option(self):
        schema = {"string": Option(str)}
        cfg = Config(schema)

        cfg.parse(['string="hello"'])
        cfg.validate()

        self.assertEqual(cfg.string, '"hello"')

    def test_required_option(self):
        schema = {"required": Option(int, required=True)}
        cfg = Config(schema)

        cfg.override({})

        with self.assertRaises(ConfigError):
            cfg.validate()

    def test_no_override_option(self):
        schema = {"opt": Option(int, override=False)}
        cfg = Config(schema)

        cfg.override({"opt": 1})
        cfg.validate()

        with self.assertRaises(ConfigError):
            cfg.override({"opt": 2})

    def test_non_strict_config(self):
        schema = {"a": Option(int), "b": Option(bool)}
        cfg = Config(schema, unknown_options="add")

        cfg.override({"a": 42, "b": True, "c": "Hello"})
        cfg.validate()

        self.assertEqual(cfg.c, "Hello")

    def test_error_unknown_option(self):
        schema = {"a": Option(int), "b": Option(bool)}
        cfg = Config(schema, unknown_options="error")

        with self.assertRaises(ConfigError):
            cfg.override({"a": 42, "b": True, "c": "Hello"})

    def test_enum(self):
        schema = {"enum": Option(Enum("str", 1, True))}
        cfg = Config(schema)

        cfg.override({"enum": "str"})
        cfg.validate()

        self.assertEqual(cfg.enum, "str")

        cfg.override({"enum": 1})
        cfg.validate()

        self.assertEqual(cfg.enum, 1)

        cfg.override({"enum": True})
        cfg.validate()

        self.assertEqual(cfg.enum, True)

        with self.assertRaises(ConfigError):
            cfg.override({"enum": 42})

    class Foo:
        def __init__(self, value: int):
            self.value = value

    def test_unregistered_type(self):
        Foo = TestConfig.Foo
        schema = {"foo": Option(Foo)}
        cfg = Config(schema)

        with self.assertRaises(ConfigError):
            cfg.override({"foo": "<10>"})

    def test_registered_type(self):
        Foo = TestConfig.Foo
        schema = {"foo": Option(Foo)}
        cfg = Config(schema)

        def convert_foo(types, value: str):
            return Foo(int(value[1:-1]))

        cfg.register_type(Foo, convert_foo)

        cfg.override({"foo": "<10>"})
        cfg.validate()

        self.assertEqual(cfg.foo.value, 10)

    def test_subconfig(self):
        subschema = {"foo": Option(int, required=True), "bar": Option(bool)}
        subcfg = Config(subschema)

        schema = {"subconfig": Option(subcfg), "foo": Option(str)}
        cfg = Config(schema)

        cfg.override({"subconfig": {"foo": 42, "bar": True}, "foo": "hello"})
        cfg.validate()

        self.assertEqual(cfg.foo, "hello")
        self.assertEqual(cfg.subconfig.foo, 42)
        self.assertEqual(cfg.subconfig.bar, True)

        cfg.clear()
        cfg.parse(["subconfig.foo=256", "subconfig.bar=False", "foo=world"])
        cfg.validate()

        self.assertEqual(cfg.foo, "world")
        self.assertEqual(cfg.subconfig.foo, 256)
        self.assertEqual(cfg.subconfig.bar, False)

        cfg.subconfig.clear()

        with self.assertRaises(ConfigError):
            cfg.validate()

        cfg.clear()
        cfg.override({"subconfig": {}})

        with self.assertRaises(ConfigError):
            cfg.validate()
