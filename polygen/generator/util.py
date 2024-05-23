import re

_LEADING_SPACE_RE = re.compile(r'^\s*')


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

    Args:
        level: Amount of indents to be prepended to lines in a block.
            If equals to 0, then indentation will be removed.
        indent: Indentation string per one level.
    """
    lines = [line for line in string.split('\n') if line.strip()]
    new_indent = indent * level
    base_indent = new_indent

    for line in lines:
        if m := _LEADING_SPACE_RE.match(line):
            if len(m.group()) < len(base_indent):
                base_indent = m.group()

    for i, line in enumerate(lines):
        if line.startswith(base_indent):
            line = line[len(base_indent):]
        lines[i] = new_indent + line

    return '\n'.join(lines)
