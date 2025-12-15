from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


async def get_cec_pv_inverters(
    db: AsyncSession,
    *,
    cec_pv_inverter_ids: list[int] = [],
):
    """todo

    Args:
        db: TODO: describe.
        cec_pv_inverter_ids: TODO: describe.
    """
    query = select(models.CECPVInverter)

    if cec_pv_inverter_ids:
        query = query.filter(
            models.CECPVInverter.cec_pv_inverter_id.in_(cec_pv_inverter_ids),
        )

    result = await db.execute(query)
    return list(result.scalars().all())


async def upsert_cec_pv_inverters_bulk(
    db: AsyncSession,
    *,
    inverters: list[interfaces.CECPVInverterCreate],
):
    """todo

    Args:
        db: TODO: describe.
        inverters: TODO: describe.
    """
    for inverter_data in inverters:
        inverter_dict = inverter_data.model_dump()

        # Check for existing inverter
        existing_query = select(models.CECPVInverter).filter_by(
            manufacturer=inverter_dict["manufacturer"],
            model_number=inverter_dict["model_number"],
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
