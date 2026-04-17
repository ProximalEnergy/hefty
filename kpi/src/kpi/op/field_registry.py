from collections.abc import MutableMapping
from typing import Any, ClassVar

from kpi.base.protocol import HasInputsProtocol
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


class FieldRegistry[F: HasInputsProtocol](metaclass=FieldRegistryMetaclass):
    _field_registry: ClassVar[dict[str, F]]
    plan: dict[str, set[str]]

    @classmethod
    def field_registry(cls) -> dict[str, F]:
        return cls._field_registry

    def __init_subclass__(cls, *, allow_override: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)

        field_registry: dict[str, F] = {}

        # inherit parent registries
        for base in list(reversed(cls.__bases__)) + [cls]:
            next_registry = base.__dict__.get("_field_registry", {})
            if not allow_override:
                intersection = field_registry.keys() & next_registry.keys()
                if len(intersection) > 0:
                    raise KeyError(
                        f"Duplicate fields defined in {cls.__name__}: {intersection}"
                    )
            field_registry.update(next_registry)

        # add local fields
        for name, value in cls.__dict__.items():
            if isinstance(value, Field):
                if name in field_registry and not allow_override:
                    raise KeyError(f"Field {name} already defined in {cls.__name__}")
                field_registry[name] = value.value
        cls._field_registry = field_registry

    def __init__(self) -> None:
        self.plan = {
            field_name: set[str]() for field_name in self.field_registry().keys()
        }

    def get(self, field_name: str) -> F:
        return self._field_registry[field_name]

    def compile(self, outputs: set[str], *, delete: bool = True) -> set[str]:
        inputs = set[str](outputs)
        plan_reversed: dict[str, set[str]] = {}
        for field_name in reversed(self.field_registry().keys()):
            if field_name in inputs:
                inputs.discard(field_name)
                calc_inputs = self.get(field_name).inputs()
                if delete:
                    plan_reversed[field_name] = calc_inputs.difference(inputs)
                else:
                    plan_reversed[field_name] = set[str]()
                inputs.update(calc_inputs)
        self.plan = dict[str, set[str]](reversed(plan_reversed.items()))
        return inputs
