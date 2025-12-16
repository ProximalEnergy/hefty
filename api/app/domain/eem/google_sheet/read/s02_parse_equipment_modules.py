import pandas as pd
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.pv_modules import get_pv_module_ids_by_manufacturer_model


async def parse_equipment_modules(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- EQUIPMENT IDS ---
    # --- Get pv module id ---
    """todo

    Args:
        db: TODO: describe.
        system: TODO: describe.
    """
    system["gsheet_module_id"] = (
        pd.factorize(
            system[["Module Manufacturer", "Module Model"]]
            .astype(str)
            .agg("-".join, axis=1),
        )[0]
        + 1
    )
    unique_modules = (
        system[["gsheet_module_id", "Module Manufacturer", "Module Model"]]
        .groupby("gsheet_module_id")
        .first()
    )
    unique_modules = unique_modules.reset_index()
    unique_manufacturers_list = unique_modules["Module Manufacturer"].tolist()
    unique_models_list = unique_modules["Module Model"].tolist()

    unique_module_ids = await get_pv_module_ids_by_manufacturer_model(
        db=db,
        pv_module_manufacturers=unique_manufacturers_list,
        pv_module_models=unique_models_list,
    )
    if None in unique_module_ids:
        # Find the rackings that have a None ID
        missing_modules = [
            f"{manufactuer} {model}"
            for manufactuer, model, id in zip(
                unique_manufacturers_list,
                unique_models_list,
                unique_module_ids,
            )
            if id is None
        ]

        # Create a user-friendly string list of the missing items
        missing_modules_str = ", ".join(map(str, missing_modules))

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not find following rackings in the database: "
                f"{missing_modules_str}",
            ),
        )
    unique_modules["pv_module_id"] = unique_module_ids

    # --- Merge the pv_module_id back into the original system DataFrame ---
    # We merge based on the columns that define a unique module type.
    # We select only the necessary columns from unique_modules for the merge.
    # `reset_index()` is needed if `gsheet_module_id` was the index, but merging on
    # manufacturer/model is safer.
    system = pd.merge(
        system,
        unique_modules[["Module Manufacturer", "Module Model", "pv_module_id"]],
        on=["Module Manufacturer", "Module Model"],
        how="left",  # Use 'left' to keep all rows from the original 'system' DataFrame
    )

    # --- Clean up temporary columns ---
    system = system.drop(
        columns=[
            "gsheet_module_id",
            "Module Manufacturer",
            "Module Model",
            "Module Bin Class",
        ],
        errors="ignore",
    )

    return system
