import re
import logging

from io import TextIOBase, StringIO
from typing import Iterable, Optional, NamedTuple, Container
from pathlib import Path


logger = logging.getLogger("polygen.preproc")


DIRECTIVE_RE = re.compile(r"(?<!\\)%% *(\w+) *%%")
DIRECTIVE_LINE_RE = re.compile(fr"(.*){DIRECTIVE_RE.pattern}(.*)\Z",
                               re.DOTALL)
NEWLINE_RE = re.compile(r"\A\n\r?\Z")


class PreprocessorDirective(NamedTuple):
    """Represents a directive found in a file."""
    string: str
    line: int
    position: int
    filename: Optional[str] = None

    def __str__(self) -> str:
        return (f"file {self.filename}:{self.position}: {self.string!r} "
                f"on line {self.line!r}")


def check_undefined_directives(
    directives: Container[str], istream: TextIOBase
) -> list[PreprocessorDirective]:
    """Check if an input string contains unknown directives.

    Returns a list of found unknown directives. If no unknown directives
    found, the resulting list is empty.

    Args:
        directives: A container of directive names.
        istream: Seekable input stream.
    """
    Dir = PreprocessorDirective
    undefined: list[PreprocessorDirective] = []
    filename = getattr(istream, "name", "<stream>")

    try:
        for i, line in enumerate(istream, 1):
            if m := DIRECTIVE_LINE_RE.match(line):
                name = m.group(2)
                if name not in directives:
                    undefined.append(Dir(name, line, m.pos, filename))
    finally:
        istream.seek(0)

    return undefined


def insert(content: str | TextIOBase,
           ostream: TextIOBase,
           prefix: str,
           ending: str) -> None:
    """Insert content into output stream.

    If `content` is stream, then it must be seekable. It is guaranteed that
    stream pointer is moved on stream start after writing.

    Prepends each non-empty line of `content` with `prefix` string. Appends
    `ending` string once, at the end of `content`.

    Args:
        content: String or stream to write into output stream. If stream,
            then it must be seekable.
        ostream: Output stream.
        prefix: String to prepend each inserting line.
        ending: Ending string.
    """
    if isinstance(content, str):
        istream = StringIO(content)
    else:
        if not content.seekable():
            raise ValueError(f"content stream must be seekable: ${content}")

        istream = content

    try:
        for line in istream:
            if not NEWLINE_RE.match(line):
                # if line is not empty
                ostream.write(prefix)
            ostream.write(line)
    finally:
        istream.seek(0)

    ostream.write(ending)


def process_stream(directives: dict[str, str | TextIOBase],
                   istream: TextIOBase,
                   ostream: TextIOBase):
    """Write data from input to output, replacing directives.

    Replaces encountered directive by its replacement from `directives`
    mapping, see `insert`. Silently replaces unknown directives by an empty
    string.

    Args:
        directives: Mapping directive name to its replacement.
        istream: Input stream.
        ostream: Output stream.
    """
    for i, line in enumerate(istream, 1):
        if m := DIRECTIVE_LINE_RE.match(line):
            start, name, ending = m.group(1, 2, 3)
            replacement = directives.get(name, '')
            insert(replacement, ostream, start, ending)
        else:
            ostream.write(line)


def create_output_filename(input_file: Path | str, add_stem=True) -> str:
    """Replace `.in` and `.input` by `.out` and return new string."""
    name = str(input_file)
    stem = r".out" if add_stem else ""
    return re.sub(r"\.in(put)?$", stem, name)


def process_file(directives: dict[str, str | TextIOBase],
                 input_file: Path,
                 output_file: Optional[Path] = None):
    """Create a new file by processing the input file.

    If `output_file` is None, then the directory for the output file is
    taken from the input file. Also output file name is created from
    the input file, see `create_output_filename`.

    If the output file already exists, it is overwritten.

    Silently replaces unknown directives by an empty string.

    Args:
        directives: Mapping directive name to its replacement.
        input_file: Input file.
        output_file: Optional output file name.
    """
    input_file = Path(input_file)

    if output_file is None:
        output_file = input_file.parent / create_output_filename(input_file)

    with open(input_file, 'r') as fin, open(output_file, 'w') as fout:
        process_stream(directives, fin, fout)


def check_undefined_directives_file(
    directives: dict, input_file: Path
) -> list[PreprocessorDirective]:
    """Check if file contains unknown directives.

    Returns a list of found unknown directives. If no unknown directives
    found, the resulting list is empty.

    Args:
        directives: A container of directive names.
        input_file: Path to a file.
    """
    with open(input_file, 'r') as fin:
        return check_undefined_directives(directives, fin)


def check_undefined_directives_batch(
    directives: dict, files: Iterable[Path]
) -> list[PreprocessorDirective]:
    """Check batch of files for unknown directives.

    Returns a list of found unknown directives for each file. If no unknown
    directives found, the resulting list is empty.

    Args:
        directives: A container of directive names.
        files: Sequence of input files.
    """
    undefined = []
    for file in files:
        undefined.extend(check_undefined_directives_file(directives, file))
    return undefined


def process_batch(directives: dict[str, str | TextIOBase],
                  files: dict[Path, Optional[Path]]):
    """Create new files by processing input files.

    Processes each file in the `files` mapping and creates output file
    with replaced directives. Unknown directives are silently replaced by
    an empty string.

    If an input file has no output file, then it is created in the same
    directory. Also output file name is a modified name of the input file,
    see `create_output_filename`.

    Overwrites existing output files.

    Args:
        directives: Mapping directive name to its replacement.
        files: Mapping input file to output file.
    """
    for input_file, output_file in files.items():
        logger.info("preprocessing %s -> %s", input_file.name, output_file)
        process_file(directives, input_file, output_file)
