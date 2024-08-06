import os
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory

from polygen.main import (
    generate_parser,
    iterate_backend_files,
    BACKEND_DIRECTORY,
    init_backend
)
from polygen.parser import Token


# How this test works.
# Test cases are represented by directories in tests/equivalency_test. Each
# test case has the following structure:
# .
# ├── 1.success
# ├── 1.success.clue
# ├── ...
# ├── 1.failure
# ├── ...
# ├── grammar.peg
# └── skip.py
#
# This test iterates over test cases and creates a TestCase class for each.
# TestCase class manages parser generation and runner setup and teardown.


# Constants
EQUIVALENCY_TEST_DIR_NAME = "equivalency_test"
GRAMMAR_FILE_NAME = "grammar.peg"
SKIP_FILE_NAME = "skip.py"
SUCCESS_FILE_STEM = ".success"
FAILURE_FILE_STEM = ".failure"
CLUE_FILE_STEM = ".clue"

SUCCESS_TEST_PREFIX = "test_success__"
FAILURE_TEST_PREFIX = "test_failure__"


# Current Working Directory used to get access to test cases
# This method would work only if the unittest was run in the project
# root directory.
CWD = Path.cwd() / "tests"
TEST_CASE_ROOT = CWD / EQUIVALENCY_TEST_DIR_NAME

# It seems that unittest picks up tests in the reversed order,
# so the order of the test addition is reversed.
TEST_CASE_DIRS = sorted(
    TEST_CASE_ROOT.iterdir(),
    key=lambda path: path.name,
    # reverse=True
)

# Set `POLYGEN_TEST_DIR` environment variable to an existing directory
# to save the results for inspection. If variable is not set,
# TemporaryDirectory is used.
TEST_NAME = "test_equivalency"
TMP_DIR = None
TEST_DIR = os.environ.get("POLYGEN_TEST_DIR")
if TEST_DIR:
    TEST_DIR = Path(TEST_DIR) / TEST_NAME
else:
    TMP_DIR = TemporaryDirectory()
    TEST_DIR = Path(TMP_DIR.name) / TEST_NAME


# Match unittest naming style
def setUpUnittestSuite():
    # For each backend:
    #     For each test case directory:
    #         create TestCase class
    #         For each individual test:
    #             add method to class
    #         add class to suite
    suite = unittest.TestSuite()

    for _backend in backends():
        gen = _backend.generator
        backend_full_name = normalize_str(
            f"{gen.NAME}_{gen.LANGUAGE}_{gen.VERSION}")

        backend_output_dir = TEST_DIR / backend_full_name
        backend_output_dir.mkdir(parents=True, exist_ok=True)

        for tc in TEST_CASE_DIRS:
            tc_full_name = f"{backend_full_name}__{normalize_str(tc.name)}"

            class TestCase(unittest.TestCase):
                test_case = tc
                backend = _backend
                output_directory = backend_output_dir

                def setUp(self):
                    grammar = self.test_case / GRAMMAR_FILE_NAME
                    generate_parser(grammar_file=grammar,
                                    backend=self.backend,
                                    output_directory=self.output_directory)
                    self.backend.runner.find_deps()
                    self.backend.runner.setup()

                    skip_file = self.test_case / SKIP_FILE_NAME
                    skip = None
                    if skip_file.exists():
                        skip = get_data(skip_file)
                    self.skip = skip

                def tearDown(self):
                    self.backend.runner.setdown()

            pattern = f"*{SUCCESS_FILE_STEM}"
            success_input_files = sorted(tc.glob(pattern))
            for input_file in success_input_files:
                addSuccessCase(TestCase, input_file, tc_full_name)

            pattern = f"*{FAILURE_FILE_STEM}"
            failure_input_files = sorted(tc.glob(pattern))
            for input_file in failure_input_files:
                addFailureCase(TestCase, input_file, tc_full_name)

            s = unittest.defaultTestLoader.loadTestsFromTestCase(TestCase)
            suite.addTest(s)

    return suite


def addSuccessCase(case_cls, input_file, test_case_full_name):
    test_full_name = (
        f"{SUCCESS_TEST_PREFIX}"
        f"{test_case_full_name}_{normalize_str(input_file.name)}"
    )

    def wrapper(self: unittest.TestCase):
        if self.skip and input_file.name in self.skip:
            reason = self.skip[input_file.name]
            self.skipTest(reason)

        clue_file_name = f"{input_file.name}{CLUE_FILE_STEM}"
        clue_file = input_file.parent / clue_file_name
        if not clue_file.exists():
            self.fail(f"clue file not found for {input_file.name}")

        clue = get_data(clue_file)
        exitcode, output = self.backend.runner.run(input_file)

        self.assertEqual(exitcode, 0)
        result = evaluate(output)
        self.assertEqual(result, clue)

    setattr(case_cls, test_full_name, wrapper)
    wrapper.__name__ = test_full_name


def addFailureCase(case_cls, input_file, test_case_full_name):
    test_full_name = (
        f"{FAILURE_TEST_PREFIX}"
        f"{test_case_full_name}_{normalize_str(input_file.name)}"
    )

    def wrapper(self: unittest.TestCase):
        if self.skip and input_file.name in self.skip:
            reason = self.skip[input_file.name]
            self.skipTest(reason)

        exitcode, output = self.backend.runner.run(input_file)
        self.assertNotEqual(exitcode, 0)

    setattr(case_cls, test_full_name, wrapper)
    wrapper.__name__ = test_full_name


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


def normalize_str(s: str) -> str:
    return s.replace(".", "_").replace("-", "_")


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(setUpUnittestSuite())
