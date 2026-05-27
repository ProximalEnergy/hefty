from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.manufacturer_model_ids import (
    lookup_ids_by_manufacturer_model_pairs,
)
from core import models


async def get_cec_pv_module_manufacturers(
    *,
    db: AsyncSession,
):
    """Returns a list of unique manufacturers of CEC PV modules.

    Args:
        db: Description for db.
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
        db: Description for db.
        manufacturer: Description for manufacturer.
    """
    query = select(models.CECPVModule.model_number).distinct()
    if manufacturer is not None:
        query = query.where(models.CECPVModule.manufacturer == manufacturer)
    result = await db.execute(query)
    return [item[0] for item in result.all()]


def get_cec_pv_modules(
    *,
    cec_pv_module_ids: list[int] | None = None,
) -> DbQuery[models.CECPVModule, Literal[False]]:
    """todo

    Args:
        cec_pv_module_ids: Description for cec_pv_module_ids.
    """
    query = select(models.CECPVModule)

    if cec_pv_module_ids:
        query = query.where(models.CECPVModule.cec_pv_module_id.in_(cec_pv_module_ids))

    return DbQuery(query=query)


async def get_cec_pv_module_ids(
    db: AsyncSession,
    *,
    pv_module_manufacturers: list[str] | None = None,
    pv_module_models: list[str] | None = None,
):
    """todo

    Args:
        db: Description for db.
        pv_module_manufacturers: Description for pv_module_manufacturers.
        pv_module_models: Description for pv_module_models.
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
    *,
    db: AsyncSession,
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
    return await lookup_ids_by_manufacturer_model_pairs(
        db=db,
        manufacturers=pv_module_manufacturers,
        model_names=pv_module_models,
        manufacturers_list_name="pv_module_manufacturers",
        model_names_list_name="pv_module_models",
        id_column=models.CECPVModule.cec_pv_module_id,
        manufacturer_column=models.CECPVModule.manufacturer,
        model_column=models.CECPVModule.model_number,
    )


async def upsert_cec_pv_modules_bulk(
    db: AsyncSession,
    *,
    modules: list[interfaces.CECPVModuleCreate],
):
    """todo

    Args:
        db: Description for db.
        modules: Description for modules.
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
