from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


def get_cec_pv_inverters(
    *,
    cec_pv_inverter_ids: list[int] | None = None,
) -> DbQuery[models.CECPVInverter, Literal[False]]:
    """Retrieve CEC PV inverters, optionally filtered by inverter IDs.

    Args:
        cec_pv_inverter_ids: Optional inverter identifiers to narrow the result.
    """
    query = select(models.CECPVInverter)

    if cec_pv_inverter_ids:
        query = query.where(
            models.CECPVInverter.cec_pv_inverter_id.in_(cec_pv_inverter_ids),
        )

    return DbQuery(query=query)


async def upsert_cec_pv_inverters_bulk(
    db: AsyncSession,
    *,
    inverters: list[interfaces.CECPVInverterCreate],
):
    """Create or update CEC PV inverter records in bulk.

    Args:
        db: Database session used for persistence.
        inverters: Inverter payloads keyed by manufacturer and model number.
    """
    for inverter_data in inverters:
        inverter_dict = inverter_data.model_dump()

        # Check for existing inverter
        existing_query = select(models.CECPVInverter).where(
            models.CECPVInverter.manufacturer == inverter_dict["manufacturer"],
            models.CECPVInverter.model_number == inverter_dict["model_number"],
        )
        result = await db.execute(existing_query)
        existing_inverter = result.scalar_one_or_none()

        if existing_inverter:
            # Only update if the new 'last_update' is more recent
            last_update = existing_inverter.last_update
            new_update = inverter_dict.get("last_update")

            if new_update and (not last_update or last_update < new_update):
                for key, value in inverter_dict.items():
                    setattr(existing_inverter, key, value)
        else:
            # Create new inverter
            new_inverter = models.CECPVInverter(**inverter_dict)
            db.add(new_inverter)

    await db.commit()
    return inverters
