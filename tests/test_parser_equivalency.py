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

TEST_CASES = sorted(TEST_CASES_DIR.iterdir(), key=lambda path: path.name)

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


class EquivalencyTestMeta(type):

    # Flip words in the name "test_case" because otherwise unittest thinks
    # that it is a test method and tries to call it.
    @staticmethod
    def case_test(self,
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

        with backend.runner as runner:
            for success_file in test_case.glob("*.success"):
                clue_file = test_case / f"{success_file.name}.clue"
                clue_data = get_data(clue_file)
                exitcode, output = runner.run(success_file)
                self.assertEqual(exitcode, 0, msg=f"Error: {output!r}")

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

                self.assertEqual(clue_data, result)

            for failure_file in test_case.glob("*.failure"):
                exitcode, output = backend.runner.run(failure_file)
                self.assertNotEqual(exitcode, 0)

    def __init__(self, name, bases, namespace):
        setattr(self, "case_test", EquivalencyTestMeta.case_test)

        for backend in backends():

            gen = backend.generator
            backend_name = f"{gen.NAME}_{gen.LANGUAGE}_{gen.VERSION}"
            backend_output_dir = TEST_DIR / backend_name
            backend_output_dir.mkdir(parents=True, exist_ok=True)

            for tc in TEST_CASES:
                test_name = f"test_{tc.name}_{normalize_name(backend_name)}"

                def wrapper(self):
                    self.case_test(
                        backend, backend_name, backend_output_dir, tc)

                setattr(self, test_name, wrapper)
                wrapper.__name__ = test_name


class EquivalencyTest(unittest.TestCase, metaclass=EquivalencyTestMeta):
    pass
