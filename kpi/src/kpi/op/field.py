from typing import Any, Literal

from kpi.base.protocol import NodeProtocol
from pydantic import BaseModel


class FieldRef[T: Any](BaseModel):
    kind: Literal["FieldRef"] = "FieldRef"
    name: str
    module: str
    qualname: str


FIELD_REGISTRY: dict[str, FieldRef] = {}


class Field[F: NodeProtocol]:
    def __init__(self, value: F, doc_header: str | None = None) -> None:
        self.value = value
        self.doc_header = doc_header
        self._name: str | None = None

    def __set_field_name__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        if self._name is None:
            raise AttributeError("name not set yet (__set_field_name__ not called)")
        return self._name

    def __set_name__(self, owner: type, name: str) -> None:
        if getattr(owner, "allow_override", False):
            return None
        if name in FIELD_REGISTRY:
            raise ValueError(f"Field {name} already registered in {owner.__name__}")
        FIELD_REGISTRY[name] = FieldRef(
            name=name,
            module=owner.__module__,
            qualname=owner.__qualname__,
        )
