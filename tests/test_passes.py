import importlib

from unittest import TestSuite
from pathlib import Path

PASSES_DIR = Path(__file__).parent / "passes"


def import_from_path(file: Path):
    spec = importlib.util.spec_from_file_location(file.stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tests(loader, tests, pattern):
    suite = TestSuite()

    for file in PASSES_DIR.iterdir():
        if not file.is_file():
            continue
        module = import_from_path(file.absolute())
        test = loader.loadTestsFromModule(module)
        suite.addTest(test)

    return suite
