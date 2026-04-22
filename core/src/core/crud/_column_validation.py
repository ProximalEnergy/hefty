from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty

ModelAttribute = InstrumentedAttribute[Any]


def split_and_validate_columns(
    *,
    columns: Sequence[ModelAttribute],
    model: type[Any],
    model_name: str | None = None,
    allowed_relationships: Sequence[ModelAttribute] | None = None,
) -> tuple[tuple[ModelAttribute, ...], tuple[ModelAttribute, ...]]:
    """Validate model attributes and split into columns and relationships.

    Args:
        columns: Attributes to validate and split.
        model: SQLAlchemy model the attributes must belong to.
        model_name: Optional display name for error messages.
        allowed_relationships: Optional relationship attributes to allow.
    """
    display_name = model_name or model.__name__
    column_attributes: list[ModelAttribute] = []
    relationship_attributes: list[ModelAttribute] = []
    for attribute in columns:
        if getattr(attribute, "class_", None) is not model:
            raise ValueError(f"Column must belong to {display_name}: {attribute}")
        attribute_property = getattr(attribute, "property", None)
        if isinstance(attribute_property, ColumnProperty):
            column_attributes.append(attribute)
            continue
        if isinstance(attribute_property, RelationshipProperty):
            if allowed_relationships is not None and not any(
                attribute is allowed_relationship
                for allowed_relationship in allowed_relationships
            ):
                raise ValueError(
                    "Only mapped "
                    f"{display_name} column attributes are allowed: {attribute}"
                )
            relationship_attributes.append(attribute)
            continue
        raise ValueError(
            f"Only mapped {display_name} column attributes are allowed: {attribute}"
        )
    return tuple(column_attributes), tuple(relationship_attributes)


def validate_model_columns(
    *,
    columns: Sequence[ModelAttribute],
    model: type[Any],
    model_name: str | None = None,
) -> tuple[ModelAttribute, ...]:
    """Validate that selected attributes are mapped columns on a model.

    Args:
        columns: Attributes to validate.
        model: SQLAlchemy model the attributes must belong to.
        model_name: Optional display name for error messages.
    """
    validated_columns, _ = split_and_validate_columns(
        columns=columns,
        model=model,
        model_name=model_name,
        allowed_relationships=(),
    )
    return validated_columns
