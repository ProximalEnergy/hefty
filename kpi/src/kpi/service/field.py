from kpi.base.protocol import HasInputsProtocol


class Field[F: HasInputsProtocol]:
    def __init__(
        self, value: F, name: str | None = None, doc: str | None = None
    ) -> None:
        self.value = value
        self._name = name
        self.doc: str = doc or ""

    def __set_field_name__(self, name: str) -> None:
        """
        Called by `SetFieldNameDict` in `FieldRegistry`'s metaclass.
        """
        self._name = name

    @property
    def name(self) -> str:
        if self._name is None:
            raise AttributeError("name not set yet (__set_field_name__ not called)")
        return self._name


class NoInputs:
    def inputs(self) -> set[str]:
        return set[str]()


class MakeField[F: HasInputsProtocol]:
    @classmethod
    def infer_doc(cls, value: F) -> Field[F]:
        return Field[F](value=value, doc=value.__doc__)
