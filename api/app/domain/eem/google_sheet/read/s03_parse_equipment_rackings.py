# import logging

import pandas as pd
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.rackings import get_racking_ids_by_manufacturer_model


async def parse_equipment_rackings(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- Get racking id ---
    system["gsheet_racking_id"] = (
        pd.factorize(
            system[["Racking Manufacturer", "Racking Model"]]
            .astype(str)
            .agg("-".join, axis=1),
        )[0]
        + 1
    )
    unique_rackings = (
        system[["gsheet_racking_id", "Racking Manufacturer", "Racking Model"]]
        .groupby("gsheet_racking_id")
        .first()
    )
    unique_rackings = unique_rackings.reset_index()
    unique_manufacturers_list = unique_rackings["Racking Manufacturer"].tolist()
    unique_models_list = unique_rackings["Racking Model"].tolist()

    unique_racking_ids = await get_racking_ids_by_manufacturer_model(
        db=db,
        racking_manufacturers=unique_manufacturers_list,
        racking_models=unique_models_list,
    )
    if None in unique_racking_ids:
        # Find the rackings that have a None ID
        missing_rackings = [
            f"{manufactuer} {model}"
            for manufactuer, model, id in zip(
                unique_manufacturers_list,
                unique_models_list,
                unique_racking_ids,
            )
            if id is None
        ]

        # Create a user-friendly string list of the missing items
        missing_rackings_str = ", ".join(map(str, missing_rackings))

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not find following rackings in the database: "
                f"{missing_rackings_str}",
            ),
        )
    unique_rackings["racking_equipment_id"] = unique_racking_ids

    system = pd.merge(
        system,
        unique_rackings[
            ["Racking Manufacturer", "Racking Model", "racking_equipment_id"]
        ],
        on=["Racking Manufacturer", "Racking Model"],
        how="left",  # Use 'left' to keep all rows from the original 'system' DataFrame
    )

    # --- Clean up temporary columns ---
    system = system.drop(
        columns=[
            "gsheet_racking_id",
            "Racking Manufacturer",
            "Racking Model",
        ],
        errors="ignore",
    )

    return system
