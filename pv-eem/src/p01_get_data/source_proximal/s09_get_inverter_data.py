import logging
from dataclasses import dataclass

import pandas as pd
import polars as pl
import sqlalchemy
from interfaces import InverterEquipmentSeries
from sqlalchemy import bindparam, text


@dataclass(slots=True)
class Inverter:
    # General inverter parameters
    """Inverter."""

    pcs_equipment_id: InverterEquipmentSeries
    manufacturer: InverterEquipmentSeries
    model: InverterEquipmentSeries

    # Operating window parameters
    voltage_mpp_min: InverterEquipmentSeries
    voltage_mpp_max: InverterEquipmentSeries
    voltage_start_up: InverterEquipmentSeries
    voltage_min: InverterEquipmentSeries
    voltage_max: InverterEquipmentSeries
    current_max: InverterEquipmentSeries

    # Temperature-dependent power characteristics
    power_max_at_reference_temp: InverterEquipmentSeries
    reference_temp: InverterEquipmentSeries

    # Efficiency parameters for reference
    voltage_nominal_efficiency: InverterEquipmentSeries
    efficiency_at_low_voltage: InverterEquipmentSeries
    efficiency_at_mid_voltage: InverterEquipmentSeries
    efficiency_at_high_voltage: InverterEquipmentSeries

    # Inverter efficiency parameters
    power_start_up: InverterEquipmentSeries
    power_ac_nominal: InverterEquipmentSeries
    power_dc_nominal: InverterEquipmentSeries
    voltage_dc_nominal: InverterEquipmentSeries
    c0: InverterEquipmentSeries
    c1: InverterEquipmentSeries
    c2: InverterEquipmentSeries
    c3: InverterEquipmentSeries
    night_tare: InverterEquipmentSeries

    @classmethod
    async def get_inverter_data(
        cls,
        unique_inverter_ids: pd.Series,
        engine: sqlalchemy.engine.Engine,
    ):
        """Get all of the relevant tracker data from the tracker table
        Args:
            * unique_inverter_ids:  polars dataframe column filtered for
            unique inverter ids
        """
        inverter_query = text(
            """
            SELECT
                *
            FROM operational.inverters
            WHERE inverter_id IN :inverter_ids
        """
        ).bindparams(bindparam("inverter_ids", expanding=True))

        with engine.connect() as conn:
            inverters = pl.read_database(
                query=inverter_query,
                connection=conn,
                execute_options={
                    "parameters": {"inverter_ids": unique_inverter_ids.tolist()}
                },
            )
        inverters_pd = inverters.to_pandas()

        if inverters_pd.empty:
            logging.critical("No inverter found for project")
            raise ValueError("No inverter found for project")

        inverters_pd = inverters_pd.rename(columns={"inverter_id": "pcs_equipment_id"})
        return cls(
            pcs_equipment_id=InverterEquipmentSeries(
                inverters_pd.loc[:, "pcs_equipment_id"]
            ),
            manufacturer=InverterEquipmentSeries(inverters_pd.loc[:, "manufacturer"]),
            model=InverterEquipmentSeries(inverters_pd.loc[:, "model"]),
            voltage_mpp_min=InverterEquipmentSeries(
                inverters_pd.loc[:, "voltage_mpp_min"]
            ),
            voltage_mpp_max=InverterEquipmentSeries(
                inverters_pd.loc[:, "voltage_mpp_max"]
            ),
            voltage_start_up=InverterEquipmentSeries(
                inverters_pd.loc[:, "voltage_start_up"]
            ),
            voltage_min=InverterEquipmentSeries(inverters_pd.loc[:, "voltage_min"]),
            voltage_max=InverterEquipmentSeries(inverters_pd.loc[:, "voltage_max"]),
            current_max=InverterEquipmentSeries(inverters_pd.loc[:, "current_max"]),
            power_max_at_reference_temp=InverterEquipmentSeries(
                inverters_pd.loc[:, "power_max_at_reference_temp"]
            ),
            reference_temp=InverterEquipmentSeries(
                inverters_pd.loc[:, "reference_temp"]
            ),
            voltage_nominal_efficiency=InverterEquipmentSeries(
                inverters_pd.loc[:, "voltage_nominal_efficiency"]
            ),
            efficiency_at_low_voltage=InverterEquipmentSeries(
                inverters_pd.loc[:, "efficiency_at_low_voltage"]
            ),
            efficiency_at_mid_voltage=InverterEquipmentSeries(
                inverters_pd.loc[:, "efficiency_at_mid_voltage"]
            ),
            efficiency_at_high_voltage=InverterEquipmentSeries(
                inverters_pd.loc[:, "efficiency_at_high_voltage"]
            ),
            power_start_up=InverterEquipmentSeries(
                inverters_pd.loc[:, "power_start_up"]
            ),
            power_ac_nominal=InverterEquipmentSeries(
                inverters_pd.loc[:, "power_ac_nominal"]
            ),
            power_dc_nominal=InverterEquipmentSeries(
                inverters_pd.loc[:, "power_dc_nominal"]
            ),
            voltage_dc_nominal=InverterEquipmentSeries(
                inverters_pd.loc[:, "voltage_dc_nominal"]
            ),
            c0=InverterEquipmentSeries(inverters_pd.loc[:, "c0"]),
            c1=InverterEquipmentSeries(inverters_pd.loc[:, "c1"]),
            c2=InverterEquipmentSeries(inverters_pd.loc[:, "c2"]),
            c3=InverterEquipmentSeries(inverters_pd.loc[:, "c3"]),
            night_tare=InverterEquipmentSeries(inverters_pd.loc[:, "night_tare"]),
        )
