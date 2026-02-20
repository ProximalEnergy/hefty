import logging
from dataclasses import dataclass

import pandas as pd
import polars as pl
import sqlalchemy
from interfaces import RackingEquipmentSeries
from sqlalchemy import bindparam, text


@dataclass(slots=True)
class Racking:
    """Racking."""

    racking_equipment_id: RackingEquipmentSeries
    racking_type_id: RackingEquipmentSeries
    manufacturer: RackingEquipmentSeries
    model: RackingEquipmentSeries
    max_rotation_angle: RackingEquipmentSeries
    min_rotation_angle: RackingEquipmentSeries
    pile_height: RackingEquipmentSeries
    structure_shading_factor: RackingEquipmentSeries
    rear_mismatch_factor: RackingEquipmentSeries

    @classmethod
    async def get_racking_data(
        cls,
        unique_racking_ids: pd.Series,
        engine: sqlalchemy.engine.Engine,
    ):
        """Get all of the relevant tracker data from the tracker table
        Args:
            * unique_tracker_ids:  polars dataframe column filtered for
            unique tracker ids
        """
        racking_query = text(
            """
            SELECT
                racking_id,
                racking_type_id,
                manufacturer,
                model,
                max_rotation_angle,
                min_rotation_angle,
                pile_height,
                structure_shading_factor,
                rear_mismatch_factor
            FROM operational.rackings
            WHERE racking_id IN :racking_ids
        """
        ).bindparams(bindparam("racking_ids", expanding=True))

        with engine.connect() as conn:
            rackings = pl.read_database(
                query=racking_query,
                connection=conn,
                execute_options={
                    "parameters": {"racking_ids": unique_racking_ids.tolist()}
                },
            )
        rackings_pd = rackings.to_pandas()

        if rackings_pd.empty:
            logging.critical("No racks found for project")
            raise ValueError("No racks found for project")

        rackings_pd = rackings_pd.rename(columns={"racking_id": "racking_equipment_id"})
        return cls(
            racking_equipment_id=RackingEquipmentSeries(
                rackings_pd.loc[:, "racking_equipment_id"]
            ),
            racking_type_id=RackingEquipmentSeries(
                rackings_pd.loc[:, "racking_type_id"]
            ),
            manufacturer=RackingEquipmentSeries(rackings_pd.loc[:, "manufacturer"]),
            model=RackingEquipmentSeries(rackings_pd.loc[:, "model"]),
            max_rotation_angle=RackingEquipmentSeries(
                rackings_pd.loc[:, "max_rotation_angle"]
            ),
            min_rotation_angle=RackingEquipmentSeries(
                rackings_pd.loc[:, "min_rotation_angle"]
            ),
            pile_height=RackingEquipmentSeries(rackings_pd.loc[:, "pile_height"]),
            structure_shading_factor=RackingEquipmentSeries(
                rackings_pd.loc[:, "structure_shading_factor"]
            ),
            rear_mismatch_factor=RackingEquipmentSeries(
                rackings_pd.loc[:, "rear_mismatch_factor"]
            ),
        )
