from kpi.base.protocol import NodeProtocol, node_protocol


class Field[F: NodeProtocol]:
    def __init__(self, value: F, doc: str | None = None) -> None:
        self.value = value
        self._name: str | None = None
        self.doc = doc or getattr(value, "__doc__", None) or ""

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


@node_protocol
class NoInputs:
    def inputs(self) -> set[str]:
        return set[str]()
