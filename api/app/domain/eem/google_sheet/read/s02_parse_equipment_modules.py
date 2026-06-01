import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.pv_modules import get_pv_module_ids_by_manufacturer_model
from app.domain.eem.google_sheet.read._resolve_manufacturer_model_equipment_ids import (
    resolve_manufacturer_model_equipment_ids,
)


async def parse_equipment_modules(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
) -> pd.DataFrame:
    """Resolve PV module IDs from sheet manufacturer/model columns.

    Args:
        db: Async database session for equipment lookups.
        system: Google Sheet system dataframe to enrich.
    """
    return await resolve_manufacturer_model_equipment_ids(
        db=db,
        system=system,
        manufacturer_column="Module Manufacturer",
        model_column="Module Model",
        gsheet_id_column="gsheet_module_id",
        output_id_column="pv_module_id",
        entity_plural="modules",
        lookup_ids=get_pv_module_ids_by_manufacturer_model,
        lookup_manufacturers_argument="pv_module_manufacturers",
        lookup_models_argument="pv_module_models",
        extra_drop_columns=["Module Bin Class"],
    )
