from typing import ClassVar

from kpi.base.protocol import NodeProtocol
from kpi.op.field import Field


class FieldRegistry[F: NodeProtocol]:
    allow_override: ClassVar[bool] = False

    def __init__(self) -> None:
        raise NotImplementedError("FieldRegistry is not instantiable")

    @classmethod
    def field_map(cls) -> dict[str, Field[F]]:
        mapping: dict[str, Field] = {}
        for base in reversed(cls.__mro__):
            for name, field in base.__dict__.items():
                if isinstance(field, Field):
                    if name in mapping and not getattr(base, "allow_override", False):
                        raise ValueError(f"Field {name} overwritten in {base.__name__}")
                    mapping[name] = field
        return mapping

    @classmethod
    def map(cls) -> dict[str, F]:
        return {name: field.value for name, field in cls.field_map().items()}
