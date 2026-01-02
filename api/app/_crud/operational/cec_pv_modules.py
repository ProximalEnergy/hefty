from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


async def get_cec_pv_module_manufacturers(
    *,
    db: AsyncSession,
):
    """Returns a list of unique manufacturers of CEC PV modules.

    Args:
        db: TODO: describe.
    """
    query = select(models.CECPVModule.manufacturer).distinct()
    result = await db.execute(query)
    return [item[0] for item in result.all()]


async def get_cec_pv_module_models_given_manufacturer(
    *,
    db: AsyncSession,
    manufacturer: str | None,
):
    """Returns a list of CEC PV module models given manufacturer

    Args:
        db: TODO: describe.
        manufacturer: TODO: describe.
    """
    query = select(models.CECPVModule.model_number).distinct()
    if manufacturer is not None:
        query = query.where(models.CECPVModule.manufacturer == manufacturer)
    result = await db.execute(query)
    return [item[0] for item in result.all()]


async def get_cec_pv_modules(
    db: AsyncSession,
    *,
    cec_pv_module_ids: list[int] | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        cec_pv_module_ids: TODO: describe.
    """
    query = select(models.CECPVModule)

    if cec_pv_module_ids:
        query = query.where(models.CECPVModule.cec_pv_module_id.in_(cec_pv_module_ids))

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_cec_pv_module_ids(
    db: AsyncSession,
    *,
    pv_module_manufacturers: list[str] | None = None,
    pv_module_models: list[str] | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        pv_module_manufacturers: TODO: describe.
        pv_module_models: TODO: describe.
    """
    query = select(models.CECPVModule.cec_pv_module_id)

    if pv_module_manufacturers:
        query = query.where(
            models.CECPVModule.manufacturer.in_(pv_module_manufacturers),
        )

    if pv_module_models:
        query = query.where(models.CECPVModule.model_number.in_(pv_module_models))

    result = await db.execute(query)
    results = result.all()
    return [item[0] for item in results]


async def get_cec_pv_module_ids_by_manufacturer_model(
    db: AsyncSession,
    *,
    pv_module_manufacturers: list[str],
    pv_module_models: list[str],
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
        and_(
            models.CECPVModule.manufacturer == manuf,
            models.CECPVModule.model_number == model,
        )
        for manuf, model in unique_input_pairs
    ]
    combined_filter = or_(*pair_conditions)

    # 3. Execute a single query to fetch all matching modules
    # Select the id, manufacturer, and model to build the lookup map
    query = select(
        models.CECPVModule.cec_pv_module_id,
        models.CECPVModule.manufacturer,
        models.CECPVModule.model_number,
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


async def upsert_cec_pv_modules_bulk(
    db: AsyncSession,
    *,
    modules: list[interfaces.CECPVModuleCreate],
):
    """todo

    Args:
        db: TODO: describe.
        modules: TODO: describe.
    """
    for module_data in modules:
        module_dict = module_data.model_dump()

        # Check for existing module
        existing_query = select(models.CECPVModule).where(
            models.CECPVModule.manufacturer == module_dict["manufacturer"],
            models.CECPVModule.model_number == module_dict["model_number"],
        )
        result = await db.execute(existing_query)
        existing_module = result.scalar_one_or_none()

        if existing_module:
            # Only update if the new 'last_update' is more recent
            last_update = existing_module.last_update
            new_update = module_dict.get("last_update")

            if new_update and (not last_update or last_update < new_update):
                for key, value in module_dict.items():
                    setattr(existing_module, key, value)
                db.add(existing_module)
        else:
            # Create new_module
            new_module = models.CECPVModule(**module_dict)
            db.add(new_module)

    await db.commit()
    return modules
