import os
import unittest
import logging

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Iterator

from polygen.main import (
    Backend,
    generate_parser,
    find_backend_file,
    iterate_backend_files,
    BACKEND_DIRECTORY,
    init_backend
)
from polygen.parser import Token


logger = logging.getLogger("polygen.equivalency")


# How does this test work.
# Test cases are represented by directories in equivalency/data. Each
# test case is of the following structure:
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
# TestCase class manages parser generation, runner setup, runner execution, and
# runner teardown.


# Constants
EQUIVALENCY_TEST_DIR_NAME = "data"
GRAMMAR_FILE_NAME = "grammar.peg"
SKIP_FILE_NAME = "skip.py"
SUCCESS_FILE_STEM = ".success"
FAILURE_FILE_STEM = ".failure"
CLUE_FILE_STEM = ".clue"

SUCCESS_TEST_PREFIX = "test_success__"
FAILURE_TEST_PREFIX = "test_failure__"

CWD = Path(__file__).absolute().parent
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
def setUpUnittestSuite(backend_name: Optional[str]):
    # For each backend:
    #     For each test case directory:
    #         create TestCase class
    #         For each individual test:
    #             add method to class
    #         add class to suite
    suite = unittest.TestSuite()

    for _backend in backends(backend_name):
        gen = _backend.generator
        backend_full_name = normalize_str(
            f"{gen.NAME}_{gen.LANGUAGE}_{gen.VERSION}")

        backend_output_dir = TEST_DIR / backend_full_name
        backend_output_dir.mkdir(parents=True, exist_ok=True)

        for tc in TEST_CASE_DIRS:
            tc_full_name = f"{backend_full_name}__{normalize_str(tc.name)}"
            test_output_directory = backend_output_dir / normalize_str(tc.name)

            class TestCase(unittest.TestCase):
                test_case = tc
                backend = _backend
                output_directory = test_output_directory

                def setUp(self):
                    self.output_directory.mkdir(exist_ok=True)
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
        f"{test_case_full_name}__{normalize_str(input_file.name)}"
    )

    copy_input_file = case_cls.output_directory / input_file.name
    copy_input_file.write_bytes(input_file.read_bytes())

    clue_file_name = f"{input_file.name}{CLUE_FILE_STEM}"
    clue_file = input_file.parent / clue_file_name
    copy_clue_file = case_cls.output_directory / clue_file_name
    copy_clue_file.write_bytes(clue_file.read_bytes())

    def wrapper(self: unittest.TestCase):
        logger.info("testing success: %s", test_full_name)

        if self.skip and input_file.name in self.skip:
            reason = self.skip[input_file.name]
            self.skipTest(reason)

        if not copy_clue_file.exists():
            self.fail(f"clue file not found for {input_file.name}")

        clue = get_data(copy_clue_file)
        exitcode, output = self.backend.runner.run(copy_input_file)

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

    copy_input_file = case_cls.output_directory / input_file.name
    copy_input_file.write_bytes(input_file.read_bytes())

    def wrapper(self: unittest.TestCase):
        logger.info("testing failure: %s", test_full_name)

        if self.skip and input_file.name in self.skip:
            reason = self.skip[input_file.name]
            self.skipTest(reason)

        exitcode, output = self.backend.runner.run(copy_input_file)
        self.assertNotEqual(exitcode, 0)

    setattr(case_cls, test_full_name, wrapper)
    wrapper.__name__ = test_full_name


def backends(backend_name: Optional[str] = None) -> Iterator[Backend]:
    if backend_name is not None:
        file = find_backend_file(backend_name, [BACKEND_DIRECTORY])
        yield init_backend(file, [])
    else:
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
