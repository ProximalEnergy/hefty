# import logging

import pandas as pd
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.inverters import get_inverter_ids_by_manufacturer_model


async def parse_equipment_inverters(
    *,
    db: AsyncSession,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- Get racking id ---
    system["gsheet_inverter_id"] = (
        pd.factorize(
            system[["PCS Manufacturer", "PCS Model"]].astype(str).agg("-".join, axis=1),
        )[0]
        + 1
    )
    unique_inverters = (
        system[["gsheet_inverter_id", "PCS Manufacturer", "PCS Model"]]
        .groupby("gsheet_inverter_id")
        .first()
    )
    unique_inverters = unique_inverters.reset_index()
    unique_manufacturers_list = unique_inverters["PCS Manufacturer"].tolist()
    unique_models_list = unique_inverters["PCS Model"].tolist()

    unique_inverter_ids = await get_inverter_ids_by_manufacturer_model(
        db=db,
        inverter_manufacturers=unique_manufacturers_list,
        inverter_models=unique_models_list,
    )
    if None in unique_inverter_ids:
        # Find the inverters that have a None ID
        missing_inverters = [
            f"{manufactuer} {model}"
            for manufactuer, model, id in zip(
                unique_manufacturers_list,
                unique_models_list,
                unique_inverter_ids,
            )
            if id is None
        ]

        # Create a user-friendly string list of the missing items
        missing_inverters_str = ", ".join(map(str, missing_inverters))

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not find following inverters in the database: "
                f"{missing_inverters_str}",
            ),
        )
    unique_inverters["inverter_equipment_id"] = unique_inverter_ids

    system = pd.merge(
        system,
        unique_inverters[["PCS Manufacturer", "PCS Model", "inverter_equipment_id"]],
        on=["PCS Manufacturer", "PCS Model"],
        how="left",  # Use 'left' to keep all rows from the original 'system' DataFrame
    )

    # --- Clean up temporary columns ---
    system = system.drop(
        columns=[
            "gsheet_inverter_id",
            "PCS Manufacturer",
            "PCS Model",
        ],
        errors="ignore",
    )

    return system
