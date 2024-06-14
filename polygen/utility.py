import string

from typing import Any, Literal


def isiterable(obj: Any) -> bool:
    """Check if an object is iterable, but not string."""
    if isinstance(obj, str):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def reindent(string: str,
             level: int,
             indent='    ') -> str:
    """Align the multiline string to the given indent level.

    Split the multiline string into lines, determine the minimum indentation
    level, remove the minimal indentation and apply the given indentation.

    Minimum indentation means that if one line is indented, say, with
    two spaces, and the second line is indented with four spaces, then
    their relative indentation will be preserved:

    ```
      line 1
        line 2
    ```

    Will be converted to (suppose that indent='    ' and level=1)

    ```
        line1
          line2
    ```

    Works only with spaces.

    Args:
        level: Amount of indents to be prepended to lines in a block.
            If equals to 0, then indentation will be removed.
        indent: Indentation string per one level.
    """
    lines = [line for line in string.split('\n')]
    empty_lines: set[int] = set()
    new_indent = indent * level
    base_indent = None

    for i, line in enumerate(lines):
        stripped_len = len(line.lstrip(' '))
        if stripped_len == 0:
            empty_lines.add(i)
            continue
        whitespace_len = len(line) - stripped_len
        if base_indent is None:
            base_indent = ' ' * whitespace_len
        if len(base_indent) > whitespace_len:
            base_indent = ' ' * whitespace_len

    indent_len = len(base_indent)
    for i, line in enumerate(lines):
        if i not in empty_lines:
            lines[i] = new_indent + line[indent_len:]

    return '\n'.join(lines)


_PRINTABLE = set(string.printable)
_WHITESPACE = set(string.whitespace)


def code_to_char(code: int) -> str:
    """Convert character code to character.

    If the character is whitespace, then its representation will be returned.
    If the character is not printable, its unicode representation will be
    returned
    """
    c = chr(code)
    if c in _PRINTABLE:
        if c in _WHITESPACE:
            return repr(c)[1:-1]
        return c
    code = hex(code)[2:].rjust(4, '0')
    return fr"\u{code}"


WrapStringMode = Literal[
    "auto",
    "double",
    "single",
    "force_double",
    "force_single"
]


def wrap_string(s: str, mode: WrapStringMode = "auto") -> str:
    """Wrap string in quotes.

    Allows to choose, which quotation mark to use.

    Modes:
        auto: By default. Choose the appropriate quotation mark type.
            If both single and double marks are appeared in the string,
            then escape single marks and use single mark.

        double: Prefer double quotes, if no double quotes appeared or both
            single and double quotes appeared.

        single: Prefer single quotes, if no single quotes appeared or both
            single and double quotes appeared.

        force_double: Use double quotes. Escape double quotes in the string.

        force_single: Use single quotes. Escape single quotes in the string.
    """
    q = "'"
    single, double = "'" in s, '"' in s
    if mode in ("auto", "single", "double"):
        if single and double:
            if mode == "double":
                s, q = s.replace('"', '\\"'), '"'
            elif mode == "single":
                s, q = s.replace("'", "\\'"), "'"
            else:
                s = s.replace("'", "\\'")
        elif single:
            q = '"'
        elif double:
            q = "'"
        else:
            if mode == "double":
                q = '"'
            elif mode == "single":
                q = "'"
        return f"{q}{s}{q}"
    elif mode == "force_double":
        s, q = s.replace('"', '\\"'), '"'
    elif mode == "force_single":
        s, q = s.replace("'", "\\'"), "'"
    else:
        raise ValueError(f"incorrect mode: {mode}")
    return f"{q}{s}{q}"
