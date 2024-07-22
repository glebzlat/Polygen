import unittest
import os

from pathlib import Path
from tempfile import TemporaryDirectory

from polygen.main import (
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


class TestGenerateParser(unittest.TestCase):

    def test_generate(self):
        for backend in backends():

            gen = backend.generator
            backend_name = f"{gen.NAME}_{gen.LANGUAGE}_{gen.VERSION}"
            backend_output_dir = TEST_DIR / backend_name
            backend_output_dir.mkdir(parents=True, exist_ok=True)

            backend.runner.find_deps()

            for tc in TEST_CASES:
                tc_output_dir = backend_output_dir / tc.name
                tc_output_dir.mkdir(exist_ok=True)

                grammar_file = tc / "grammar.peg"
                generate_parser(grammar_file=grammar_file,
                                backend=backend,
                                output_directory=tc_output_dir)

                for success_file in tc.glob("*.success"):
                    clue_file = tc / f"{success_file.name}.clue"
                    clue_data = get_data(clue_file)

                    with backend.runner as runner:
                        exitcode, output = runner.run(success_file)
                    self.assertEqual(exitcode, 0, msg=f"Error: {output!r}")

                    try:
                        result = evaluate(output)
                    except Exception as e:
                        msg = (
                            f"Error: "
                            f"backend {backend_name}; "
                            f"test_case {tc.name}; "
                            f"file {success_file.name}; "
                            f"exception_type {type(e).__name__}; "
                            f"message {str(e)!r}"
                        )
                        raise AssertionError(msg) from e

                    self.assertEqual(clue_data, result)
