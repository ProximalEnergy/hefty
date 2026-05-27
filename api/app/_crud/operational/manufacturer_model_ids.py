import uuid
from typing import Literal

from core.db_query import DbQuery, OutputType
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute


async def lookup_ids_by_manufacturer_model_pairs(
    *,
    db: AsyncSession,
    manufacturers: list[str],
    model_names: list[str],
    manufacturers_list_name: str,
    model_names_list_name: str,
    id_column: InstrumentedAttribute[int],
    manufacturer_column: InstrumentedAttribute[str],
    model_column: InstrumentedAttribute[str],
    company_id_column: InstrumentedAttribute[uuid.UUID] | None = None,
    company_id: uuid.UUID | None = None,
) -> list[int | None]:
    """Look up entity IDs for parallel manufacturer/model lists, preserving order.

    Args:
        db: The database session.
        manufacturers: Manufacturer names, one per row to resolve.
        model_names: Model names aligned element-wise with manufacturers.
        manufacturers_list_name: Input list name for length-mismatch errors.
        model_names_list_name: Input list name for length-mismatch errors.
        id_column: Primary-key column to select.
        manufacturer_column: Manufacturer column on the entity table.
        model_column: Model column on the entity table.
        company_id_column: Optional company filter column.
        company_id: When set with company_id_column, restrict matches.

    Returns:
        IDs in input order, or None when a pair is not found.

    Raises:
        ValueError: When manufacturers and model_names differ in length.
    """
    if len(manufacturers) != len(model_names):
        raise ValueError(
            f"Input lists '{manufacturers_list_name}' and "
            f"'{model_names_list_name}' must have the same length.",
        )

    if not manufacturers:
        return []

    input_pairs: list[tuple[str, str]] = list(zip(manufacturers, model_names))
    unique_input_pairs: set[tuple[str, str]] = set(input_pairs)

    pair_conditions = [
        and_(manufacturer_column == manuf, model_column == model)
        for manuf, model in unique_input_pairs
    ]
    combined_filter = or_(*pair_conditions)

    if company_id is not None and company_id_column is not None:
        combined_filter = and_(combined_filter, company_id_column == company_id)

    query = select(id_column, manufacturer_column, model_column).where(
        combined_filter,
    )

    result = await DbQuery[tuple[int, str, str], Literal[False]](
        query=query,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )

    found_lookup: dict[tuple[str, str], int] = {
        (manuf, model): int(entity_id) for entity_id, manuf, model in result
    }

    return [found_lookup.get(pair) for pair in input_pairs]
