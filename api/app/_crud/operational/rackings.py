import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.manufacturer_model_ids import (
    lookup_ids_by_manufacturer_model_pairs,
)
from core import models


async def get_rackings(
    *,
    db: AsyncSession,
    racking_ids: list[int] | None = None,
):
    """todo

    Args:
        db: Description for db.
        racking_ids: Description for racking_ids.
    """
    query = select(models.Racking)

    if racking_ids:
        query = query.where(models.Racking.racking_id.in_(racking_ids))

    result = await db.execute(query)
    return result.scalars().all()


async def get_racking_manufacturers(
    *,
    db: AsyncSession,
    company_id: uuid.UUID | None = None,
):
    """Returns a list of unique manufacturers of rackings.

    Args:
        db: Description for db.
        company_id: Description for company_id.
    """
    query = select(models.Racking.manufacturer).distinct()

    if company_id is not None:
        query = query.where(models.Racking.company_id == company_id)

    query = query.where(models.Racking.manufacturer.isnot(None))

    result = await db.execute(query)
    return result.scalars().all()


async def get_racking_models_given_manufacturer(
    *,
    db: AsyncSession,
    manufacturer: str | None,
    company_id: uuid.UUID | None = None,
):
    """Returns a list of racking models given manufacturer

    Args:
        db: Description for db.
        manufacturer: Description for manufacturer.
        company_id: Description for company_id.
    """

    query = select(models.Racking.model).distinct()
    if manufacturer is not None:
        query = query.where(models.Racking.manufacturer == manufacturer)
    if company_id is not None:
        query = query.where(models.Racking.company_id == company_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_racking_ids(
    *,
    db: AsyncSession,
    racking_manufacturer: list[str] | None = None,
    racking_model: list[str] | None = None,
    company_id: uuid.UUID | None = None,
):
    """todo

    Args:
        db: Description for db.
        racking_manufacturer: Description for racking_manufacturer.
        racking_model: Description for racking_model.
        company_id: Description for company_id.
    """
    query = select(models.Racking)

    if racking_manufacturer:
        query = query.where(models.Racking.manufacturer.in_(racking_manufacturer))

    if racking_model:
        query = query.where(models.Racking.model.in_(racking_model))

    if company_id is not None:
        query = query.where(models.Racking.company_id == company_id)

    result = await db.execute(query)
    return [r.racking_id for r in result.scalars().all()]


async def get_racking_ids_by_manufacturer_model(
    *,
    db: AsyncSession,
    racking_manufacturers: list[str],
    racking_models: list[str],
    company_id: uuid.UUID | None = None,
) -> list[int | None]:
    """
    Finds the racking_id for each given manufacturer/model pair, preserving order.

    Takes parallel lists of manufacturers and models representing specific rackings
    to look up. It queries the database once to find IDs for all matching pairs.
    The output list contains the racking_id for each input pair at the
    corresponding index, or None if that specific pair was not found.

    Args:
        db: The database session.
        racking_manufacturers: A list of manufacturer names.
        racking_models: A list of model names, corresponding element-wise
                          to racking_manufacturers.
        company_id: Optional UUID to filter rackings by company.

    Returns:
        A list of the same length as the input lists, containing the
        racking_id (int) for each found pair, or None if the pair
        was not found in the database. The order matches the input lists.

    Raises:
        ValueError: If the input lists 'racking_manufacturers' and
                    'racking_models' do not have the same length.
    """
    return await lookup_ids_by_manufacturer_model_pairs(
        db=db,
        manufacturers=racking_manufacturers,
        model_names=racking_models,
        manufacturers_list_name="racking_manufacturers",
        model_names_list_name="racking_models",
        id_column=models.Racking.racking_id,
        manufacturer_column=models.Racking.manufacturer,
        model_column=models.Racking.model,
        company_id_column=models.Racking.company_id,
        company_id=company_id,
    )


async def create_racking(
    *,
    db: AsyncSession,
    racking: interfaces.PVRackings,
):
    """
    Creates a new racking in the database if it doesn't exist,
    otherwise updates the existing racking.

    Args:
        db: Database session
        racking: PVRackings interface object containing all racking details

    Returns:
        The created or updated racking object
    """
    if racking.racking_id is not None:
        # Update existing racking
        query = select(models.Racking).where(
            and_(
                models.Racking.racking_id == racking.racking_id,
                models.Racking.company_id == racking.company_id,
            )
        )
        result = await db.execute(query)
        db_racking = result.scalar_one_or_none()
        if not db_racking:
            raise ValueError(f"No racking found with ID {racking.racking_id}")
    else:
        # Create new racking with next available ID
        query = (
            select(models.Racking)
            .where(models.Racking.company_id == racking.company_id)
            .order_by(models.Racking.racking_id.desc())
        )
        result = await db.execute(query)
        max_racking = result.scalar_one_or_none()

        racking_id = 1 if max_racking is None else max_racking.racking_id + 1
        db_racking = models.Racking(
            racking_id=racking_id, company_id=racking.company_id
        )
        db.add(db_racking)

    # Update all attributes using bulk update
    racking_data = racking.model_dump(exclude={"racking_id"})
    for attr, value in racking_data.items():
        setattr(db_racking, attr, value)

    await db.commit()
    await db.refresh(db_racking)
    return db_racking
