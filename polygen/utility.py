from typing import Any


def isiterable(obj: Any) -> bool:
    """Check if an object is iterable, but not string."""
    if isinstance(obj, str):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def wrap_string(string: str, double=True) -> str:
    if double:
        string = string.replace('"', '\\"')
        return f'"{string}"'
    else:
        string = string.replace("'", "\\'")
        return f"'{string}'"


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
