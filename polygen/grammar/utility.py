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
