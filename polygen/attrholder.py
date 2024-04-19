class AttributeHolder:
    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = [repr(arg) for arg in self._get_args()]
        star_args = {}
        for name, value in self._get_kwargs():
            if name.isidentifier():
                arg_strings.append(f"{name}={value!r}")
            else:
                star_args[name] = value
        if star_args:
            arg_strings.append(f"**{star_args:r}")
        args = ', '.join(arg_strings)
        return f"{type_name}({args})"

    def __str__(self):
        return self.__repr__()

    def _get_kwargs(self):
        return list(self.__dict__.items())

    def _get_args(self):
        return []


class ArgsRepr(AttributeHolder):
    def _get_kwargs(self):
        return []
