import unittest

from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import contextmanager

from polygen.generator.preprocessor import (
    create_output_filename,
    insert,

    check_undefined_directives,
    process_stream,

    check_undefined_directives_file,
    process_file,

    check_undefined_directives_batch
)

TMP_DIR = TemporaryDirectory()
TEST_DIR = Path.cwd() / 'tests' / 'preprocessor_tests'


class Test_create_output_filename(unittest.TestCase):

    def test_replace_in_out(self):
        clue = "file.out"
        output = create_output_filename("file.in")
        self.assertEqual(output, clue)
        output = create_output_filename("file.input")
        self.assertEqual(output, clue)

    def test_remove_in(self):
        output = create_output_filename("file.in", add_stem=False)
        self.assertEqual(output, "file")

    def test_does_not_change_parents(self):
        file = Path("dir.in/parent.input/file.in")
        output = Path(create_output_filename("dir.in/parent.input/file.in"))
        self.assertEqual(output, file.parent / "file.out")


class Test_insert(unittest.TestCase):

    def test_insert_appends_content_to_stream(self):
        content = "hello\nworld"
        ostream = StringIO()
        prefix = ">>> "
        ending = ";"

        insert(content, ostream, prefix, ending)

        clue = ">>> hello\n>>> world;"
        self.assertEqual(ostream.getvalue(), clue)

        ostream.seek(0)
        content = StringIO(content)
        insert(content, ostream, prefix, ending)
        self.assertEqual(ostream.getvalue(), clue)

    def test_do_not_write_prefix_on_empty_lines(self):
        content = "hello\n\nworld"
        ostream = StringIO()
        prefix = ">>> "
        ending = ";"

        insert(content, ostream, prefix, ending)

        clue = ">>> hello\n\n>>> world;"
        self.assertEqual(ostream.getvalue(), clue)

    def test_write_prefix_if_no_content(self):
        content = ""
        ostream = StringIO()
        prefix = ">>> "
        ending = ";"

        insert(content, ostream, prefix, ending)

        clue = ">>> ;"
        self.assertEqual(ostream.getvalue(), clue)


class Test_check_undefined_in_stream(unittest.TestCase):

    def test_collect_undefined(self):
        data = """%% directive_1 %%
123%% directive_2 %%
        """
        istream = StringIO(data)
        undef = check_undefined_directives({}, istream)

        self.assertEqual(len(undef), 2)

        dir1, dir2 = undef
        self.assertEqual(dir1.string, "directive_1")
        self.assertEqual(dir1.line, 1)
        self.assertEqual(dir1.position, 3)
        self.assertEqual(dir1.filename, "<stream>")
        self.assertEqual(dir2.string, "directive_2")
        self.assertEqual(dir2.line, 2)
        self.assertEqual(dir2.position, 6)

    def test_ignore_defined(self):
        data = """
            %% message %%
            %% greeting %%
            %% farewell %%
        """
        istream = StringIO(data)
        directives = {"greeting": "Hello, World"}
        undef = check_undefined_directives(directives, istream)

        self.assertEqual(len(undef), 2)
        self.assertEqual(undef[0].string, "message")
        self.assertEqual(undef[1].string, "farewell")

    def test_ignore_escaped(self):
        data = r"\%% message %%"
        istream = StringIO(data)
        undef = check_undefined_directives({}, istream)

        self.assertEqual(len(undef), 0)


class Test_process_stream(unittest.TestCase):

    def test_ignore_undefined(self):
        data = """
            1st line begin %% d1 %% end
            2nd line begin %% d2 %% end
            3rd line begin %% d3 %% end
        """
        istream = StringIO(data)
        ostream = StringIO()
        directives = {"d1": "Hello", "d3": "Goodbye"}

        process_stream(directives, istream, ostream)

        clue = """
            1st line begin Hello end
            2nd line begin  end
            3rd line begin Goodbye end
        """
        self.assertEqual(ostream.getvalue(), clue)


class FileSystemManager:
    def __init__(self, root_directory):
        self.root = Path(root_directory)
        self.root.mkdir(exist_ok=True)

    @contextmanager
    def directory(self, name: str) -> Path:
        save = self.root
        try:
            self.root = self.root / name
            self.root.mkdir(exist_ok=True)
            yield self.root
        finally:
            self.root = save

    def copy_files(self,
                   source: Path,
                   files: str | list[str]) -> list[Path] | Path:
        if not source.exists():
            return

        if files == "*":
            paths = []
            for f in source.iterdir():
                if not f.is_file():
                    continue
                dest = self.root / f.name
                dest.touch()
                dest.write_bytes(f.read_bytes())
                paths.append(dest)
            return paths

        if isinstance(files, list):
            paths = []
            for f in map(source.joinpath, files):
                if not f.is_file():
                    continue
                dest = self.root / f.name
                dest.touch()
                dest.write_bytes(f.read_bytes())
                paths.append(dest)
            return paths

        else:
            f = source / files
            if not f.is_file():
                return
            dest = self.root / f.name
            dest.touch()
            dest.write_bytes(f.read_bytes())
            return dest


fs = FileSystemManager(TMP_DIR.name)


class Test_check_undefined_file(unittest.TestCase):

    def test_filename(self):
        with fs.directory("check_undefined_file_1"):
            input = fs.copy_files(TEST_DIR, "file_a.input")

            undef = check_undefined_directives_file({}, input)

            self.assertEqual(len(undef), 1)
            self.assertEqual(undef[0].filename, str(input))


class Test_process_file(unittest.TestCase):

    def test_auto_create_output_file(self):
        with fs.directory("process_file_1") as path:
            input, clue = fs.copy_files(TEST_DIR,
                                        ["file_a.input", "file_a.clue"])
            output = path / "file_a.out"

            directives = {"greeting": "Hello, World"}
            process_file(directives, input)

            self.assertTrue(output.exists())
            self.assertEqual(output.read_bytes(), clue.read_bytes())

    def test_create_given_filename(self):
        with fs.directory("process_file_2") as path:
            input, clue = fs.copy_files(TEST_DIR,
                                        ["file_a.input", "file_a.clue"])
            output_dir = path / "output"
            output_dir.mkdir()
            output = output_dir / "file_a.out"

            directives = {"greeting": "Hello, World"}
            process_file(directives, input, output)

            self.assertTrue(output.exists())


class Test_check_undefined_batch(unittest.TestCase):

    def test_batch(self):
        with fs.directory("check_undefined_batch_1"):
            files = fs.copy_files(
                TEST_DIR, ["file_c.input", "file_d.input", "file_e.input"])

            undef = check_undefined_directives_batch({}, files)

            self.assertEqual(len(undef), 3)

            for input_file, directive in zip(files, undef):
                self.assertEqual(str(input_file), directive.filename)
