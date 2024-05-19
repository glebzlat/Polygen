import os
import unittest
import shutil

from io import StringIO
from tempfile import NamedTemporaryFile, TemporaryDirectory

from polygen.generator.preprocessor import (
    NoSuchDirective,
    FilePreprocessorError,
    Preprocessor,
    FilePreprocessor
)

TEST_DIR = os.path.join(os.getcwd(), 'tests', 'preprocessor_tests')


class PreprocessorTestMetaClass(type):
    """
    Metaclass for Preprocessor testing.

    Preprocessor test classes must define the following attributes:
        input_data: Input data string.
        directives: dict[DirectiveName, SubstitutionString]

    The following attributes are interchangable:
        output_data: The expected result.
        error: tuple[ExceptionType, dict[AttributeName, Value]].
            If defined, then a fact, that exception with type ExceptionType
            and the exact attribute values as defined in a dict, is raised,
            will be tested.

    If `error` attribute is defined, then `output_data` is not necessary,
    because the preprocessing result is invalid and will not be tested.
    """

    def __init__(cls, name, bases, body):
        if name == 'PreprocessorTestBase':
            return

        def test_preprocess(self):
            istream = StringIO(self.input_data)
            ostream = StringIO()

            p = Preprocessor(directives=self.directives)

            error = getattr(self, 'error', None)
            if error is None:
                p.process_stream(istream, ostream)

                ostream.seek(0)
                result = ostream.read()
                self.assertEqual(result, self.output_data)

            else:
                exc_type, attrs = error
                with self.assertRaises(exc_type) as context:
                    p.process_stream(istream, ostream)

                exception = context.exception
                for name, value in attrs.items():
                    attr_value = getattr(exception, name)
                    self.assertEqual(attr_value, value)

        setattr(cls, 'test_preprocess', test_preprocess)


bases = (unittest.TestCase,)
PreprocessorTestBase = (
    PreprocessorTestMetaClass('PreprocessorTestBase', bases, {}))


class TestWithoutDirectives(PreprocessorTestBase):
    data = "hello world"

    input_data = data
    output_data = data
    directives = {}


class TestMultilineWODirectives(PreprocessorTestBase):
    data = """
first line
second line
"""
    input_data = data
    output_data = data
    directives = {}


class TestNoReplace(PreprocessorTestBase):
    data = "text without directives"
    input_data = data
    output_data = data
    directives = {
        'mydirective': 'Hello, World!'
    }


class TestNotADirective_1(PreprocessorTestBase):
    data = "This is not a directive: % greeting %"
    input_data = data
    output_data = data
    directives = {
        'greeting': 'Hello World'
    }


class TestNotADirective_2(PreprocessorTestBase):
    data = "This is not a directive: %% greeting %"
    input_data = data
    output_data = data
    directives = {
        'greeting': 'Hello World'
    }


class TestNotADirective_3(PreprocessorTestBase):
    data = "This is not a directive: % greeting %%"
    input_data = data
    output_data = data
    directives = {
        'greeting': 'Hello World'
    }


class TestNotADirective_4(PreprocessorTestBase):
    data = "This is not a directive: %%\ngreeting %%"
    input_data = data
    output_data = data
    directives = {
        'greeting': 'Hello World'
    }


class TestReplace(PreprocessorTestBase):
    directive_name = "mydirective"
    directive = f"%% {directive_name} %%"
    substitution = "Hello, World"

    data = "Substitute here: {dir}!"
    input_data = data.format(dir=directive)
    output_data = data.format(dir=substitution)

    directives = {
        directive_name: substitution
    }


class TestDirectiveNotFoundOneLine(PreprocessorTestBase):
    input_data = "Well, try to substitute this: %% greting %%"
    directives = {
        'greeting': "Hello, World"
    }
    error = (NoSuchDirective, {'directive': 'greting', 'lineno': 1})


class TestDirectiveNotFound(PreprocessorTestBase):
    input_data = """
        Well,
        try to substitute this:
        %% greting %%
    """
    directives = {
        'greeting': "Hello, World"
    }
    error = (NoSuchDirective, {
        'directive': 'greting', 'lineno': 4, 'filename': '<stream>'})


class TestPreservePrefix(PreprocessorTestBase):
    input_data = """
    # %% comment %%
    """
    output_data = """
    # multi
    # line
    # comment
    """
    directives = {
        'comment': "multi\nline\ncomment"
    }


class TestPreservePrefixAndPostfix(PreprocessorTestBase):
    input_data = """
    # %% comment %%  # at the end
    """
    output_data = """
    # multi
    # line
    # comment  # at the end
    """
    directives = {
        'comment': "multi\nline\ncomment"
    }


class FilePreprocessorTestMetaClass(type):
    """Metaclass for FilePreprocessor testing.

    Test class must define the following attributes:
        input_files: List of filenames. Files must be placed in `TEST_DIR`
            directory.
        directives: A substitutions mapping.

    Optional attributes:
        error: A tuple[ExceptionType, dict[AttributeName, AttributeValue]].
            See PreprocessorTestMetaClass for the description.
    """

    def __init__(cls, name, bases, body):
        if name == 'FilePreprocessorTest':
            return

        tests_path = TEST_DIR

        def input_to_clue(s: str):
            name = s.split('.')[0]
            return os.path.join(tests_path, f'{name}.clue')

        input_files = cls.input_files
        clue_files = (input_to_clue(i) for i in input_files)
        input_files = (os.path.join(tests_path, i) for i in input_files)

        def test_process(self):
            files = {i: NamedTemporaryFile('r+t') for i in input_files}
            files_names = {i: tmp.name for i, tmp in files.items()}

            try:
                p = FilePreprocessor(self.directives)
                p.process(files_names)

                for tmp, clue in zip(files.values(), clue_files):
                    tmp.seek(0)
                    with open(clue, 'r', encoding='utf-8') as clue_file:
                        result = tmp.read()
                        clue = clue_file.read()
                        self.assertEqual(result, clue)

            finally:
                for tmp in files.values():
                    tmp.close()

        def test_raises(self):
            files = {i: NamedTemporaryFile('r+t') for i in input_files}
            files_names = {i: tmp.name for i, tmp in files.items()}

            try:
                p = FilePreprocessor(self.directives)

                exc_type, attrs = self.error
                with self.assertRaises(exc_type) as context:
                    p.process(files_names)

                exception = context.exception
                for name, value in attrs.items():
                    attr_value = getattr(exception, name)
                    self.assertEqual(attr_value, value)

                for tmp in files.values():
                    self.assertEqual(tmp.tell(), 0)

            finally:
                for tmp in files.values():
                    tmp.close()

        if getattr(cls, 'error', None) is not None:
            setattr(cls, 'test_raises', test_raises)
        else:
            setattr(cls, 'test_process', test_process)


FilePreprocessorTest = (
    FilePreprocessorTestMetaClass('FilePreprocessorTest', bases, {}))


class ProcessSingleFileTest(FilePreprocessorTest):
    input_files = ['single_file.input']
    directives = {
        'greeting': "Hello, World"
    }


class ProcessTwoFilesTest(FilePreprocessorTest):
    input_files = ['file_a.input', 'file_b.input']
    directives = {
        'greeting': "Hello, World"
    }


class MultipleErroneousFilesTest(FilePreprocessorTest):

    file_c = 'file_c.skel'
    file_d = 'file_d.skel'
    file_c_full = os.path.join(TEST_DIR, file_c)
    file_d_full = os.path.join(TEST_DIR, file_d)

    input_files = [file_c, file_d]
    directives = {
        'greeting': "Hello, World"
    }
    error = (FilePreprocessorError, {'errors': (
        NoSuchDirective('foo', 1, file_c_full),
        NoSuchDirective('bar', 1, file_d_full)
    )})

    def test_no_file_created(self):
        file_list = os.listdir(TEST_DIR)
        self.assertNotIn('file_c', file_list)
        self.assertNotIn('file_d', file_list)


class OneErroneousFileTest(FilePreprocessorTest):
    """Error happens in the second file in the list, and no file is created."""

    file_e = 'file_e.skel'
    file_f = 'file_f.skel'
    file_f_full = os.path.join(TEST_DIR, file_f)

    input_files = [file_e, file_f]
    directives = {
        'greeting': "Hello, World"
    }

    error = (FilePreprocessorError, {'errors': (
        NoSuchDirective('foo', 1, file_f_full),
    )})

    def test_no_file_created(self):
        file_list = os.listdir(TEST_DIR)
        self.assertNotIn('file_e', file_list)
        self.assertNotIn('file_f', file_list)


class InheritFilenamesTest(unittest.TestCase):

    def test_filenames(self):
        directives = {
            'greeting': "Hello, World"
        }
        p = FilePreprocessor(directives)

        input_files = ['file_g.skel', 'file_h.test.skel']
        clue_files = ['file_g', 'file_h.test']

        with TemporaryDirectory() as tmpdir:

            # Copy files from test files directory to the destination,
            # because FilePreprocessor uses input file's path for output
            # file
            orig_files = [os.path.join(TEST_DIR, f) for f in input_files]
            input_files = [os.path.join(tmpdir, f) for f in input_files]
            for orig, dest in zip(orig_files, input_files):
                shutil.copy(orig, dest)

            p.process([(f, None) for f in input_files])

            file_list = os.listdir(tmpdir)
            for clue_file in clue_files:
                self.assertIn(clue_file, file_list)
