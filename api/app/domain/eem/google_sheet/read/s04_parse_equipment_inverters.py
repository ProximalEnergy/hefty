import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.inverters import get_inverter_ids_by_manufacturer_model
from app.domain.eem.google_sheet.read._resolve_manufacturer_model_equipment_ids import (
    resolve_manufacturer_model_equipment_ids,
)


async def parse_equipment_inverters(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
) -> pd.DataFrame:
    """Resolve inverter equipment IDs from sheet PCS manufacturer/model columns.

    Args:
        db: Async database session for equipment lookups.
        system: Google Sheet system dataframe to enrich.
    """
    return await resolve_manufacturer_model_equipment_ids(
        db=db,
        system=system,
        manufacturer_column="PCS Manufacturer",
        model_column="PCS Model",
        gsheet_id_column="gsheet_inverter_id",
        output_id_column="inverter_equipment_id",
        entity_plural="inverters",
        lookup_ids=get_inverter_ids_by_manufacturer_model,
        lookup_manufacturers_argument="inverter_manufacturers",
        lookup_models_argument="inverter_models",
    )
