def enum_evaluable_repr(cls):
    """
    Changes default enum class' representation to evaluable

    The default repr of an enum member "FOO" with value 42 of an
    enum "MyEnum" is:

    ```python
    MyEnum.FOO: 42>
    ```

    `_enum_evaluable_repr` makes it:

    ```python
    MyEnum.FOO
    ```
    """

    def _repr(self):
        class_name = self.__class__.__name__
        self_name = self.name
        return f"{class_name}.{self_name}"

    cls.__repr__ = _repr
    return cls
