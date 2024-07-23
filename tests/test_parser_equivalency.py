import unittest
import os

from pathlib import Path
from tempfile import TemporaryDirectory

from polygen.main import (
    Backend,
    generate_parser,
    iterate_backend_files,
    BACKEND_DIRECTORY,
    init_backend
)
from polygen.parser import Token

CWD = Path.cwd() / "tests"
TEST_CASES_DIR = CWD / "parser_test_cases"

# Add cases in reverse order, because it seems that unittest picks up
# the last added test first
TEST_CASES = sorted(TEST_CASES_DIR.iterdir(), key=lambda path: path.name,
                    reverse=True)

TMP_DIR = None
TEST_DIR = os.environ.get("POLYGEN_TEST_DIR")
if TEST_DIR:
    TEST_DIR = Path(TEST_DIR) / "test_generate"
else:
    TMP_DIR = TemporaryDirectory()
    TEST_DIR = Path(TMP_DIR.name) / "test_generate"


def backends():
    for file in iterate_backend_files([BACKEND_DIRECTORY]):
        yield init_backend(file, [])


def evaluate(data):
    # do not supply builtin functions, because these files are intended
    # to be just a result without any calculations or side-effects
    return eval(data, {"__builtins__": {}, "Token": Token})


def get_data(clue_file):
    with open(clue_file, 'r', encoding="UTF-8") as fin:
        return evaluate(fin.read())


def normalize_name(s: str) -> str:
    return s.replace(".", "_").replace("-", "_")


def test_case(self,
              backend: Backend,
              backend_name: str,
              backend_output_dir: Path,
              test_case: Path):
    backend.runner.find_deps()

    tc_output_dir = backend_output_dir / test_case.name
    tc_output_dir.mkdir(exist_ok=True)

    grammar_file = test_case / "grammar.peg"
    generate_parser(grammar_file=grammar_file,
                    backend=backend,
                    output_directory=tc_output_dir)

    skip: dict[str, str]  # case file name -> reason
    skip_cases_file = test_case / "skip.py"
    if skip_cases_file.exists():
        skip = get_data(skip_cases_file)
    else:
        skip = {}

    with backend.runner as runner:
        for success_file in test_case.glob("*.success"):
            reason = skip.get(success_file.name)
            if reason:
                # log this
                continue

            clue_file = test_case / f"{success_file.name}.clue"
            clue_data = get_data(clue_file)
            exitcode, output = runner.run(success_file)

            msg = (
                f"test={test_case.name} "
                f"case={success_file.name}; "
                f"{exitcode=}; "
                f"{output=};"
            )
            self.assertEqual(exitcode, 0, msg=msg)

            try:
                result = evaluate(output)
            except Exception as e:
                msg = (
                    f"Error: "
                    f"backend {backend_name}; "
                    f"test_case {test_case.name}; "
                    f"file {success_file.name}; "
                    f"exception_type {type(e).__name__}; "
                    f"message {str(e)!r}"
                )
                raise AssertionError(msg) from e

            self.assertEqual(result, clue_data, msg=msg)

        for failure_file in test_case.glob("*.failure"):
            reason = skip.get(failure_file.name)
            if reason:
                # log this
                continue

            exitcode, output = backend.runner.run(failure_file)
            self.assertNotEqual(exitcode, 0)


class EquivalencyTestMeta(type):

    def __init__(self, name, bases, namespace):

        # TestAdder is just a capture for variables
        class TestAdder:
            def __init__(self, backend, backend_name, output_dir, tc):
                self.backend = backend
                self.backend_name = backend_name
                self.output_dir = output_dir
                self.tc = tc

            def add_test(self, obj):
                def wrapper(_self):
                    test_case(
                        _self,
                        self.backend,
                        self.backend_name,
                        self.output_dir,
                        self.tc
                    )

                test_name = (
                    f"test_{self.tc.name}_{normalize_name(self.backend_name)}"
                )
                setattr(obj, test_name, wrapper)
                wrapper.__name__ = test_name

        for backend in backends():

            gen = backend.generator
            backend_name = f"{gen.NAME}_{gen.LANGUAGE}_{gen.VERSION}"
            backend_output_dir = TEST_DIR / backend_name
            backend_output_dir.mkdir(parents=True, exist_ok=True)

            for tc in TEST_CASES:
                (TestAdder(backend, backend_name, backend_output_dir, tc)
                 .add_test(self))


class EquivalencyTest(unittest.TestCase, metaclass=EquivalencyTestMeta):
    pass
