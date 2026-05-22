from kpi.base.protocol import NodeProtocol


class Field[F: NodeProtocol]:
    def __init__(self, value: F, doc_header: str | None = None) -> None:
        self.value = value
        self._name: str | None = None
        self.doc_header = doc_header
        self._owner_module: str = ""
        self._owner_qualname: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        # should have already been set by the FieldRegistry metaclass,
        # but just in case, it's here too
        self._name = name
        self._owner_module = owner.__module__
        self._owner_qualname = owner.__qualname__

    @property
    def name(self) -> str:
        if self._name is None:
            raise AttributeError("name not set yet (__set_name__ not called)")
        return self._name
