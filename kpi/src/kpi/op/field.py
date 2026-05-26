from typing import Literal

from kpi.base.protocol import NodeProtocol
from pydantic import BaseModel


class FieldRef(BaseModel):
    kind: Literal["FieldCodeRef"] = "FieldCodeRef"
    name: str = "_no_name_set"
    module: str = "_no_module_set"
    qualname: str = "_no_qualname_set"


class Field[F: NodeProtocol]:
    def __init__(self, value: F, doc_header: str | None = None) -> None:
        self.value = value
        self.doc_header = doc_header
        self.ref = FieldRef()

    def __set_name__(self, owner: type, name: str) -> None:
        # should have already been set by the FieldRegistry metaclass,
        # but just in case, it's here too
        self.ref.name = name
        self.ref.module = owner.__module__
        self.ref.qualname = owner.__qualname__
