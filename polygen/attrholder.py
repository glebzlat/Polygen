from typing import Callable, Any, Iterable


class AttributeHolder:
    def __repr__(self) -> str:
        return self._repr(repr)

    def __str__(self) -> str:
        return self._repr(str)

    def _repr(self, repr_fn: Callable[[Any], str]) -> str:
        type_name = type(self).__name__
        arg_strings = [repr_fn(arg) for arg in self._get_args()]
        star_args = {}
        for name, value in self._get_kwargs():
            if name.startswith('_'):
                continue
            if name.isidentifier():
                value_repr = repr_fn(value)
                arg_strings.append(f"{name}={value_repr}")
            else:
                star_args[name] = value
        if star_args:
            args_repr = repr_fn(star_args)
            arg_strings.append(f"**{args_repr}")
        args = ', '.join(arg_strings)
        return f"{type_name}({args})"

    def _get_kwargs(self) -> Iterable[tuple[str, Any]]:
        return self.__dict__.items()

    def _get_args(self) -> Iterable[Any]:
        return ()


class ArgsRepr(AttributeHolder):
    def _repr(self, repr_fn: Callable[[Any], str]) -> str:
        type_name = type(self).__name__
        arg_strings = (repr_fn(arg) for arg in self._get_args())
        args = ', '.join(arg_strings)
        return f"{type_name}({args})"
