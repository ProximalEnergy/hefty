from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from core import models


async def get_ercot_resources_options(*, deep: bool):
    if deep:
        options = (
            # Load the main 'settlement_point' relationship...
            selectinload(models.Resource.settlement_point).options(
                selectinload(models.SettlementPoint.settlement_point_type),
                selectinload(models.SettlementPoint.load_zone),
            ),
            # Other top-level relationships are separate
            selectinload(models.Resource.qse),
            selectinload(models.Resource.dme),
        )
    else:
        # This part remains the same
        options = (
            noload(models.Resource.settlement_point),
            noload(models.Resource.qse),
            noload(models.Resource.dme),
        )

    return options


async def get_ercot_resources(*, db: AsyncSession, deep: bool = False):
    options = await get_ercot_resources_options(deep=deep)
    query = select(models.Resource).options(*options)
    result = await db.execute(query)
    return result.scalars().all()


async def get_ercot_resource(*, db: AsyncSession, resource_id: int, deep: bool = False):
    options = await get_ercot_resources_options(deep=deep)
    query = (
        select(models.Resource)
        .options(*options)
        .filter(models.Resource.resource_id == resource_id)
    )
    result = await db.execute(query)
    return result.scalars().first()
