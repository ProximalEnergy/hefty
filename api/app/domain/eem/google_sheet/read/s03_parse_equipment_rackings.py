import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.rackings import get_racking_ids_by_manufacturer_model
from app.domain.eem.google_sheet.read._resolve_manufacturer_model_equipment_ids import (
    resolve_manufacturer_model_equipment_ids,
)


async def parse_equipment_rackings(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
) -> pd.DataFrame:
    """Resolve racking equipment IDs from sheet manufacturer/model columns.

    Args:
        db: Async database session for equipment lookups.
        system: Google Sheet system dataframe to enrich.
    """
    return await resolve_manufacturer_model_equipment_ids(
        db=db,
        system=system,
        manufacturer_column="Racking Manufacturer",
        model_column="Racking Model",
        gsheet_id_column="gsheet_racking_id",
        output_id_column="racking_equipment_id",
        entity_plural="rackings",
        lookup_ids=get_racking_ids_by_manufacturer_model,
        lookup_manufacturers_argument="racking_manufacturers",
        lookup_models_argument="racking_models",
    )
