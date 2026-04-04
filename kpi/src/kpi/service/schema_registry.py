from typing import Any, ClassVar, Protocol, overload

import xarray as xr
from kpi.base.protocol import SchemaClassProtocol, SchemaProtocol
from kpi.service.observer import observe


class HasObjectRegistry(Protocol):
    object_registry: dict[str, SchemaProtocol]


class Schema:
    _name: str | None

    def __init__(self, value: SchemaClassProtocol, name: str | None = None) -> None:
        self.value = value
        self._name = name

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @overload
    def __get__(self, instance: None, owner: type) -> SchemaClassProtocol: ...

    @overload
    def __get__(self, instance: HasObjectRegistry, owner: type) -> SchemaProtocol: ...

    def __get__(
        self, instance: None | HasObjectRegistry, owner: type
    ) -> SchemaProtocol | SchemaClassProtocol:
        if instance is None:
            return self.value

        if self._name is None:
            raise AttributeError("name not set yet (__set_name__ not called)")

        name = self._name

        if name not in instance.object_registry:
            raise AttributeError(f"object {name} not found in registry")

        return instance.object_registry[name]


class SchemaRegistry:
    class_registry: ClassVar[dict[str, SchemaClassProtocol]] = {}
    _field_registry: ClassVar[dict[str, Any]]
    object_registry: dict[str, SchemaProtocol]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        class_registry: dict[str, SchemaClassProtocol] = {}

        # inherit parent registries
        for base in reversed(cls.__mro__):
            class_registry.update(getattr(base, "class_registry", {}))

        # add local fields
        for name, value in cls.__dict__.items():
            if isinstance(value, Schema):
                class_registry[name] = value.value
        cls.class_registry = class_registry

        field_registry: dict[str, Any] = {}
        for schema_name, schema_class in class_registry.items():
            intersection = field_registry.keys() & schema_class.field_registry().keys()
            if len(intersection) > 0:
                raise KeyError(
                    f"Duplicate fields defined in {schema_name}: {intersection}"
                )
            field_registry |= schema_class.field_registry()

        cls._field_registry = field_registry

    @classmethod
    def field_registry(cls) -> dict[str, Any]:
        return cls._field_registry

    def __init__(self) -> None:
        # instantiate all the classes
        self.object_registry = {
            name: self.class_registry[name]() for name in self.class_registry.keys()
        }
        self.schema_plan = list[str](self.object_registry.keys())

    def compile(self, outputs: set[str], *, delete: bool = True) -> set[str]:
        inputs = set[str](outputs)
        reverse_schema_plan: list[str] = []
        for schema_name in reversed(self.object_registry.keys()):
            schema = self.object_registry[schema_name]
            outputs_created = inputs.intersection(schema.field_registry().keys())
            if len(outputs_created) > 0:
                reverse_schema_plan.append(schema_name)
            inputs.difference_update(outputs_created)
            inputs.update(schema.compile(outputs_created, delete=delete))
        self.schema_plan = list[str](reversed(reverse_schema_plan))
        return inputs

    @property
    def plan(self) -> dict[str, set[str]]:
        plan: dict[str, set[str]] = {}
        for schema_name in self.schema_plan:
            plan |= self.object_registry[schema_name].plan
        return plan

    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        for schema_name in self.schema_plan:
            with observe():
                dataset = self.object_registry[schema_name].run(dataset=dataset)
        return dataset
