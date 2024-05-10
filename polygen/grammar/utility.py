import re

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


_UNESCAPED_DOUBLE_QUOTE_RE = re.compile(r'(?<!\\)"')


def wrap_string(string: str) -> str:
    if _UNESCAPED_DOUBLE_QUOTE_RE.match(string):
        string = string.replace('"', '\\"')
    return f'"{string}"'
