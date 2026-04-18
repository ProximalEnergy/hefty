from collections.abc import MutableMapping
from typing import Any, ClassVar

from kpi.base.protocol import NodeProtocol
from kpi.op.field import Field


class SetFieldNameDict(dict):
    def __setitem__(self, key, value):
        if hasattr(value, "__set_field_name__"):
            value.__set_field_name__(key)
        super().__setitem__(key, value)


class FieldRegistryMetaclass(type):
    @classmethod
    def __prepare__(
        metacls, name: str, bases: tuple[type, ...], /, **kwds: Any
    ) -> MutableMapping[str, object]:
        """
        This method is called before __new__.
        It must return a dictionary-like object that will store the class attributes.
        """
        return SetFieldNameDict()


class FieldRegistry[F: NodeProtocol](metaclass=FieldRegistryMetaclass):
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
