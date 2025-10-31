import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app.logger import logger
from core import models


async def get_inverters(
    *,
    db: AsyncSession,
    inverter_ids: list[int] | None = None,
):
    query = select(models.Inverter)

    if inverter_ids:
        query = query.filter(models.Inverter.inverter_id.in_(inverter_ids))
    result = await db.execute(query)
    return result.scalars().all()


async def get_inverter_by_id(
    *,
    db: AsyncSession,
    inverter_id: int,
    company_id: uuid.UUID | None = None,
):
    """
    Get a single inverter by its ID, optionally filtered by company.

    Args:
        db: Database session
        inverter_id: ID of the inverter to retrieve
        company_id: Optional company ID to filter by

    Returns:
        The inverter object if found, None otherwise
    """
    query = select(models.Inverter).filter(models.Inverter.inverter_id == inverter_id)

    if company_id is not None:
        query = query.filter(models.Inverter.company_id == company_id)

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_inverter_manufacturers(
    *,
    db: AsyncSession,
    company_id: uuid.UUID | None = None,
):
    """
    Returns a list of unique manufacturers of inverters.
    """
    logger.info(
        f"CRUD: get_inverter_manufacturers called with company_id: {company_id}"
    )

    query = (
        select(models.Inverter.manufacturer)
        .filter(models.Inverter.manufacturer.isnot(None))
        .distinct()
    )

    if company_id is not None:
        logger.info(f"CRUD: Filtering by company_id: {company_id}")
        query = query.filter(models.Inverter.company_id == company_id)
    else:
        logger.info("CRUD: No company_id filter applied - returning all manufacturers")

    result = await db.execute(query)
    manufacturers = result.scalars().all()

    logger.info(
        f"CRUD: Query returned {len(manufacturers)} manufacturers: {manufacturers}"
    )
    return manufacturers


async def get_inverter_models_given_manufacturer(
    *,
    db: AsyncSession,
    manufacturer: str | None,
    company_id: uuid.UUID | None = None,
):
    """
    Returns a list of inverter models given manufacturer
    """

    query = select(models.Inverter.model).distinct()
    if manufacturer is not None:
        query = query.filter(models.Inverter.manufacturer == manufacturer)
    if company_id is not None:
        query = query.filter(models.Inverter.company_id == company_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_inverter_ids(
    *,
    db: AsyncSession,
    inverter_manufacturer: list[str] | None = None,
    inverter_model: list[str] | None = None,
    company_id: uuid.UUID | None = None,
):
    query = select(models.Inverter.inverter_id)

    if inverter_manufacturer:
        query = query.filter(models.Inverter.manufacturer.in_(inverter_manufacturer))

    if inverter_model:
        query = query.filter(models.Inverter.model.in_(inverter_model))

    if company_id is not None:
        query = query.filter(models.Inverter.company_id == company_id)

    result = await db.execute(query)
    return result.scalars().all()


async def get_inverter_ids_by_manufacturer_model(
    *,
    db: AsyncSession,
    inverter_manufacturers: list[str],
    inverter_models: list[str],
    company_id: uuid.UUID | None = None,
) -> list[int | None]:
    """
    Finds the inverter_id for each given manufacturer/model pair, preserving order.

    Takes parallel lists of manufacturers and models representing specific inverters
    to look up. It queries the database once to find IDs for all matching pairs.
    The output list contains the inverter_id for each input pair at the
    corresponding index, or None if that specific pair was not found.

    Args:
        db: The database session.
        inverter_manufacturers: A list of manufacturer names.
        inverter_models: A list of model names, corresponding element-wise
                          to inverter_manufacturers.
        company_id: Optional UUID to filter inverters by company.

    Returns:
        A list of the same length as the input lists, containing the
        inverter_id (int) for each found pair, or None if the pair
        was not found in the database. The order matches the input lists.

    Raises:
        ValueError: If the input lists 'inverter_manufacturers' and
                    'inverter_models' do not have the same length.
    """
    if len(inverter_manufacturers) != len(inverter_models):
        raise ValueError(
            "Input lists 'inverter_manufacturers' and 'inverter_models' "
            "must have the same length.",
        )

    if not inverter_manufacturers:  # If lists are empty
        return []

    # 1. Create unique pairs from input to optimize the DB query
    # We use a set first to avoid redundant OR conditions in the SQL query
    # Store original pairs with index for reconstruction later if needed, but
    # simple zip is sufficient here as we iterate through original list at the end.
    input_pairs: list[tuple[str, str]] = list(
        zip(inverter_manufacturers, inverter_models),
    )
    unique_input_pairs: set[tuple[str, str]] = set(input_pairs)

    # 2. Build the OR condition for the database query
    # Find rows where (manufacturer=m1 AND model=mdl1) OR
    # (manufacturer=m2 AND model=mdl2) ...
    pair_conditions = [
        and_(models.Inverter.manufacturer == manuf, models.Inverter.model == model)
        for manuf, model in unique_input_pairs
    ]
    combined_filter = or_(*pair_conditions)

    # Add company_id filter if provided
    if company_id is not None:
        combined_filter = and_(
            combined_filter, models.Inverter.company_id == company_id
        )

    # 3. Execute a single query to fetch all matching inverters
    # Select the id, manufacturer, and model to build the lookup map
    query = select(
        models.Inverter.inverter_id,
        models.Inverter.manufacturer,
        models.Inverter.model,
    ).filter(combined_filter)

    result = await db.execute(query)
    results = result.all()  # Fetches [(id, manuf, model), ...] for all found inverters

    # 4. Build a lookup dictionary: {(manufacturer, model): id}
    # This maps the found manufacturer/model pairs back to their IDs
    found_inverters_lookup: dict[tuple[str, str], int] = {
        (manuf, model): mod_id for mod_id, manuf, model in results
    }

    # 5. Construct the final ordered list based on the *original* input pairs
    ordered_ids: list[int | None] = []
    for manuf, model in input_pairs:
        # Look up the pair in our dictionary of found inverters.
        # If the pair wasn't found in the query results, .get() returns None.
        inverter_id = found_inverters_lookup.get((manuf, model), None)
        ordered_ids.append(inverter_id)

    return ordered_ids


async def create_inverter(
    *,
    db: AsyncSession,
    inverter: interfaces.Inverter,
):
    """
    Creates a new inverter in the database if it doesn't exist,
    otherwise updates the existing inverter.

    Args:
        db: Database session
        inverter: Inverter interface object containing all inverter details

    Returns:
        The created or updated inverter object
    """

    if inverter.inverter_id is not None:
        # Update existing inverter
        query = select(models.Inverter).filter(
            and_(
                models.Inverter.inverter_id == inverter.inverter_id,
                models.Inverter.company_id == inverter.company_id,
            )
        )
        result = await db.execute(query)
        db_inverter = result.scalar_one_or_none()
        if not db_inverter:
            raise ValueError(f"No inverter found with ID {inverter.inverter_id}")
    else:
        # Create new inverter with next available ID
        query = (
            select(models.Inverter)
            .filter(models.Inverter.company_id == inverter.company_id)
            .order_by(models.Inverter.inverter_id.desc())
        )
        result = await db.execute(query)
        max_id = result.scalar_one_or_none()

        inverter_id = 1 if max_id is None else max_id.inverter_id + 1
        db_inverter = models.Inverter(
            inverter_id=inverter_id, company_id=inverter.company_id
        )
        db.add(db_inverter)

    # Update all attributes using bulk update
    inverter_data = inverter.model_dump(exclude={"inverter_id", "company_id"})
    for attr, value in inverter_data.items():
        setattr(db_inverter, attr, value)

    await db.commit()
    await db.refresh(db_inverter)
    return db_inverter
