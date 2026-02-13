import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


async def get_pv_modules(
    *,
    db: AsyncSession,
    pv_module_ids: list[int] | None = None,
    company_id: uuid.UUID | None = None,
):
    """todo

    Args:
        db: Description for db.
        pv_module_ids: Description for pv_module_ids.
        company_id: Description for company_id.
    """
    query = select(models.PVModule)

    if pv_module_ids:
        query = query.where(models.PVModule.pv_module_id.in_(pv_module_ids))

    if company_id is not None:
        query = query.where(models.PVModule.company_id == company_id)

    result = await db.execute(query)
    return result.scalars().all()


async def get_pv_module_by_id(
    *,
    db: AsyncSession,
    pv_module_id: int,
    company_id: uuid.UUID | None = None,
):
    """
    Get a single PV module by its ID.

    Args:
        db: Database session
        pv_module_id: The ID of the PV module to retrieve
        company_id: Optional company ID to filter by

    Returns:
        The PV module object or None if not found
    """
    query = select(models.PVModule).where(models.PVModule.pv_module_id == pv_module_id)

    if company_id is not None:
        query = query.where(models.PVModule.company_id == company_id)

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_pv_module_manufacturers(
    *,
    db: AsyncSession,
    company_id: uuid.UUID | None = None,
):
    """Returns a list of unique manufacturers of PV modules.

    Args:
        db: Description for db.
        company_id: Description for company_id.
    """
    query = select(models.PVModule.manufacturer).distinct()

    if company_id is not None:
        query = query.where(models.PVModule.company_id == company_id)

    query = query.where(models.PVModule.manufacturer.isnot(None))
    result = await db.execute(query)
    return result.scalars().all()


async def get_pv_module_models_given_manufacturer(
    *,
    db: AsyncSession,
    manufacturer: str | None,
    company_id: uuid.UUID | None = None,
):
    """Returns a list of modules given manufacturer

    Args:
        db: Description for db.
        manufacturer: Description for manufacturer.
        company_id: Description for company_id.
    """

    query = select(models.PVModule.model).distinct()
    if manufacturer is not None:
        query = query.where(models.PVModule.manufacturer == manufacturer)
    if company_id is not None:
        query = query.where(models.PVModule.company_id == company_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_pv_module_ids(
    *,
    db: AsyncSession,
    pv_module_manufacturers: list[str] | None = None,
    pv_module_models: list[str] | None = None,
    company_id: uuid.UUID | None = None,
):
    """todo

    Args:
        db: Description for db.
        pv_module_manufacturers: Description for pv_module_manufacturers.
        pv_module_models: Description for pv_module_models.
        company_id: Description for company_id.
    """
    query = select(models.PVModule)

    if pv_module_manufacturers:
        query = query.where(models.PVModule.manufacturer.in_(pv_module_manufacturers))

    if pv_module_models:
        query = query.where(models.PVModule.model.in_(pv_module_models))

    if company_id is not None:
        query = query.where(models.PVModule.company_id == company_id)

    result = await db.execute(query)
    return [m.pv_module_id for m in result.scalars().all()]


async def get_pv_module_ids_by_manufacturer_model(
    *,
    db: AsyncSession,
    pv_module_manufacturers: list[str],
    pv_module_models: list[str],
    company_id: uuid.UUID | None = None,
) -> list[int | None]:
    """
    Finds the pv_module_id for each given manufacturer/model pair, preserving order.

    Takes parallel lists of manufacturers and models representing specific modules
    to look up. It queries the database once to find IDs for all matching pairs.
    The output list contains the pv_module_id for each input pair at the
    corresponding index, or None if that specific pair was not found.

    Args:
        db: The database session.
        pv_module_manufacturers: A list of manufacturer names.
        pv_module_models: A list of model names, corresponding element-wise
                          to pv_module_manufacturers.
        company_id: Optional UUID to filter PV modules by company.

    Returns:
        A list of the same length as the input lists, containing the
        pv_module_id (int) for each found pair, or None if the pair
        was not found in the database. The order matches the input lists.

    Raises:
        ValueError: If the input lists 'pv_module_manufacturers' and
                    'pv_module_models' do not have the same length.
    """
    if len(pv_module_manufacturers) != len(pv_module_models):
        raise ValueError(
            "Input lists 'pv_module_manufacturers' and 'pv_module_models' "
            "must have the same length.",
        )

    if not pv_module_manufacturers:  # If lists are empty
        return []

    # 1. Create unique pairs from input to optimize the DB query
    # We use a set first to avoid redundant OR conditions in the SQL query
    # Store original pairs with index for reconstruction later if needed, but
    # simple zip is sufficient here as we iterate through original list at the end.
    input_pairs: list[tuple[str, str]] = list(
        zip(pv_module_manufacturers, pv_module_models),
    )
    unique_input_pairs: set[tuple[str, str]] = set(input_pairs)

    # 2. Build the OR condition for the database query
    # Find rows where (manufacturer=m1 AND model=mdl1) OR
    # (manufacturer=m2 AND model=mdl2) ...
    pair_conditions = [
        and_(models.PVModule.manufacturer == manuf, models.PVModule.model == model)
        for manuf, model in unique_input_pairs
    ]
    combined_filter = or_(*pair_conditions)

    # Add company_id filter if provided
    if company_id is not None:
        combined_filter = and_(
            combined_filter, models.PVModule.company_id == company_id
        )

    # 3. Execute a single query to fetch all matching modules
    # Select the id, manufacturer, and model to build the lookup map
    query = select(
        models.PVModule.pv_module_id,
        models.PVModule.manufacturer,
        models.PVModule.model,
    ).where(combined_filter)

    result = await db.execute(query)
    results = result.all()  # Fetches [(id, manuf, model), ...] for all found modules

    # 4. Build a lookup dictionary: {(manufacturer, model): id}
    # This maps the found manufacturer/model pairs back to their IDs
    found_modules_lookup: dict[tuple[str, str], int] = {
        (manuf, model): mod_id for mod_id, manuf, model in results
    }

    # 5. Construct the final ordered list based on the *original* input pairs
    ordered_ids: list[int | None] = []
    for manuf, model in input_pairs:
        # Look up the pair in our dictionary of found modules.
        # If the pair wasn't found in the query results, .get() returns None.
        module_id = found_modules_lookup.get((manuf, model), None)
        ordered_ids.append(module_id)

    return ordered_ids


async def create_pv_module(
    *,
    db: AsyncSession,
    pv_module: interfaces.PVModule,
):
    """
    Creates a new PV module in the database if it doesn't exist,
    otherwise updates the existing PV module.

    Args:
        db: Database session
        pv_module: PVModule interface object containing all PV module details

    Returns:
        The created or updated PV module object
    """

    # Validate required parameters
    if (pv_module.alpha_isc is None) | (pv_module.beta_voc is None):
        raise ValueError("Missing required parameters alpha_isc or beta_voc")

    # 2. Get or Create the database object
    if pv_module.pv_module_id is not None:
        # --- UPDATE PATH: Find the existing module ---
        update_query = select(models.PVModule).where(
            models.PVModule.pv_module_id == pv_module.pv_module_id,
            models.PVModule.company_id == pv_module.company_id,
        )
        update_result = await db.execute(update_query)
        db_pv_module = update_result.scalar_one_or_none()
        # Fail fast if the ID for that company doesn't exist
        if not db_pv_module:
            raise ValueError(
                f"Update failed: No PV module found with ID {pv_module.pv_module_id}"
            )
    else:
        # --- CREATE PATH: Determine new ID and create instance ---
        create_query = select(func.max(models.PVModule.pv_module_id)).where(
            models.PVModule.company_id == pv_module.company_id
        )
        create_result = await db.execute(create_query)
        max_pv_module_id: int | None = create_result.scalar_one()
        new_id = 1 if max_pv_module_id is None else max_pv_module_id + 1

        db_pv_module = models.PVModule(
            pv_module_id=new_id, company_id=pv_module.company_id
        )
        db.add(db_pv_module)

    # 3. Update attributes on the fetched or newly created object
    # Using exclude_unset=True ensures we only update fields that were actually sent.
    update_data = pv_module.model_dump(
        exclude_unset=True, exclude={"pv_module_id", "company_id"}
    )
    for key, value in update_data.items():
        setattr(db_pv_module, key, value)

    # 4. Commit the transaction and refresh the object
    await db.commit()
    await db.refresh(db_pv_module)
    return db_pv_module
