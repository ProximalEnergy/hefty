import warnings
from collections.abc import MutableMapping
from typing import Any, ClassVar, Self

import xarray as xr
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import ContextModel
from kpi_pipeline.base.protocols import ActionProtocol, ObserverProtocol, SchemaProtocol


class DuplicateCheckingDict(dict):
    """A dictionary that raises a NameError if a key is set more than once.
    It also assigns the name to the RegistrableField instance."""

    def __setitem__(self, key, value):
        if key in self:
            raise NameError(f"Duplicate field definition found in class: '{key}'")
        if isinstance(value, Field):
            value.set_var(var=key)
        super().__setitem__(key, value)


class SchemaMetaclass(type):
    @classmethod
    def __prepare__(
        metacls, name: str, bases: tuple[type, ...], /, **kwds: Any
    ) -> MutableMapping[str, object]:
        """
        This method is called before __new__.
        It must return a dictionary-like object that will store the class attributes.
        """
        # Hand Python our "strict notebook" to use for building the class
        return DuplicateCheckingDict()

    def __new__(mcs, name, bases, attrs):
        # Create the class first
        cls = super().__new__(mcs, name, bases, attrs)

        # Store the registry as a class attribute
        cls._registry = {}  # type: ignore

        return cls

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        if not isinstance(cls, SchemaProtocol):
            raise TypeError(f"Class {cls.__name__} is not a SchemaProtocol")

        # Populate registry with all Field instances from this class and base classes
        # First, copy fields from base classes
        for base in bases:
            if isinstance(base, SchemaProtocol):
                cls._registry.update(base._registry)

        # Then, add/override with fields defined in this class
        for attr_name, attr_value in attrs.items():
            if cls._ignore_attribute_name(attr_name):
                continue
            cls._check_valid_attribute_value(attr_name, attr_value)
            cls._registry[attr_name] = attr_value


class ScopeWrappedAction[T](ActionProtocol[T]):
    def __init__(self, transform: ActionProtocol[T], scope: str):
        self.transform = transform
        self.scope = scope

    @property
    def pass_through(self) -> bool:
        return self.transform.pass_through

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> T:
        with observer.with_scope(scope=self.scope):
            return self.transform(dataset=dataset, context=context, observer=observer)

    def nominal_outputs(self) -> list[str]:
        return self.transform.nominal_outputs()

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        return self.transform.expected_inputs(outputs=outputs)

    def trim(self, *, outputs: list[str] = []) -> Self:
        return self.__class__(
            transform=self.transform.trim(outputs=outputs), scope=self.scope
        )

    def __repr__(self) -> str:
        return self.scope


class SchemaAbstract[T, K](metaclass=SchemaMetaclass):
    _registry: ClassVar[dict[str, K]]
    _allowed_attribute_type: ClassVar[type[Any]]
    _attribute_name_exceptions: ClassVar[list[str]] = ["value_registry", "export"]

    @classmethod
    def _ignore_attribute_name(cls, attr_name: str) -> bool:
        return attr_name[0] == "_" or attr_name in cls._attribute_name_exceptions

    @classmethod
    def _check_valid_attribute_value(cls, attr_name: str, attr_value: Any) -> None:
        if not isinstance(attr_value, cls._allowed_attribute_type):
            raise ValueError(
                f"Attribute {attr_name} must be type {cls._allowed_attribute_type} for {cls.__name__}"
            )

    @classmethod
    def _export(cls, scope: str | None = None) -> ActionProtocol[T]:
        raise NotImplementedError("Subclasses must implement this method")

    @classmethod
    def export(cls, scope: str | None = None) -> ScopeWrappedAction[T]:
        return ScopeWrappedAction[T](
            transform=cls._export(scope=scope),
            scope=scope or cls.__name__,
        )


class FieldSchemaAbstract[T, V](SchemaAbstract[T, Field]):
    _allowed_attribute_type = Field
    _allowed_field_value_type: type[V]

    @classmethod
    def _check_valid_attribute_value(cls, attr_name: str, attr_value: Field) -> None:
        if not isinstance(attr_value, cls._allowed_attribute_type):
            raise TypeError(
                f"Attribute {attr_name} must be type {cls._allowed_attribute_type} for {cls.__name__}"
            )
        if attr_value.value is None:
            warnings.warn(f"Field {attr_name} has no value")
            return
        if not isinstance(attr_value.value, cls._allowed_field_value_type):
            raise TypeError(
                f"Field value type {type(attr_value.value)} must be type {cls._allowed_field_value_type} for {cls.__name__}"
            )

    @classmethod
    def value_registry(cls) -> dict[str, V]:
        return {
            name: field.value
            for name, field in cls._registry.items()
            if field.value is not None
        }


class TransformFieldSchemaAbstract[V](FieldSchemaAbstract[xr.Dataset, V]):
    pass
