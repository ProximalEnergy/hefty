from collections.abc import Awaitable, Callable

import pandas as pd
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

LookupIdsByManufacturerModel = Callable[..., Awaitable[list[int | None]]]


async def resolve_manufacturer_model_equipment_ids(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
    manufacturer_column: str,
    model_column: str,
    gsheet_id_column: str,
    output_id_column: str,
    entity_plural: str,
    lookup_ids: LookupIdsByManufacturerModel,
    lookup_manufacturers_argument: str,
    lookup_models_argument: str,
    extra_drop_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Resolve DB equipment IDs for sheet manufacturer/model columns.

    Factorizes unique manufacturer/model pairs, looks up IDs, merges back into
    ``system``, and drops temporary sheet columns.

    Args:
        db: Async database session for equipment lookups.
        system: Google Sheet system dataframe to enrich.
        manufacturer_column: Column name for equipment manufacturer.
        model_column: Column name for equipment model.
        gsheet_id_column: Temporary factorized ID column name to create.
        output_id_column: Column name for resolved database equipment ID.
        entity_plural: Plural noun used in missing-equipment error messages.
        lookup_ids: Async lookup returning IDs aligned with manufacturer/model
            lists (``None`` when a pair is not found).
        lookup_manufacturers_argument: Keyword argument name for manufacturers.
        lookup_models_argument: Keyword argument name for models.
        extra_drop_columns: Additional sheet columns to remove after merge.

    Returns:
        ``system`` with ``output_id_column`` populated and sheet columns dropped.
    """
    pair_key = (
        system[[manufacturer_column, model_column]].astype(str).agg("-".join, axis=1)
    )
    system[gsheet_id_column] = pd.factorize(pair_key)[0] + 1
    unique_equipment = (
        system[[gsheet_id_column, manufacturer_column, model_column]]
        .groupby(gsheet_id_column)
        .first()
    )
    unique_equipment = unique_equipment.reset_index()
    unique_manufacturers_list = unique_equipment[manufacturer_column].tolist()
    unique_models_list = unique_equipment[model_column].tolist()

    unique_equipment_ids = await lookup_ids(
        db=db,
        **{
            lookup_manufacturers_argument: unique_manufacturers_list,
            lookup_models_argument: unique_models_list,
        },
    )
    if None in unique_equipment_ids:
        missing_equipment = [
            f"{manufacturer} {model}"
            for manufacturer, model, equipment_id in zip(
                unique_manufacturers_list,
                unique_models_list,
                unique_equipment_ids,
                strict=True,
            )
            if equipment_id is None
        ]
        missing_equipment_str = ", ".join(map(str, missing_equipment))
        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not find following {entity_plural} in the database: "
                f"{missing_equipment_str}"
            ),
        )
    unique_equipment[output_id_column] = unique_equipment_ids

    system = pd.merge(
        system,
        unique_equipment[[manufacturer_column, model_column, output_id_column]],
        on=[manufacturer_column, model_column],
        how="left",
    )

    drop_columns = [
        gsheet_id_column,
        manufacturer_column,
        model_column,
        *(extra_drop_columns or []),
    ]
    return system.drop(columns=drop_columns, errors="ignore")
