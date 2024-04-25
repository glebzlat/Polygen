from typing import overload, Self
from enum import StrEnum as _StrEnum


class StrEnum(_StrEnum):
    # mimic str.__new__'s overloads
    @overload
    def __new__(cls, object: object = ...) -> Self:
        ...

    @overload
    def __new__(cls,
                obj: object,
                encoding: str = ...,
                errors: str = ...) -> Self:
        ...

    def __new__(cls, *values):
        # when we import enum, _StrEnum.__new__ gets moved to _new_member_ when
        # the "final" _StrEnum class is created via EnumType
        return _StrEnum._new_member_(cls, *values)



