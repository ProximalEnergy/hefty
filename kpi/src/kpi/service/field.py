class Field[F]:
    def __init__(self, value: F, name: str | None = None) -> None:
        self.value = value
        self._name = name

    def __set_field_name__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        if self._name is None:
            raise AttributeError("name not set yet (__set_field_name__ not called)")
        return self._name


class NoInputs:
    def inputs(self) -> set[str]:
        return set[str]()
