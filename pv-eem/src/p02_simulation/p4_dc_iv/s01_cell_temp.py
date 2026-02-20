from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import (
    Indeces,
    MetTimeSeries,
    ModuleEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


class ModelThermal(StrEnum):
    """ModelThermal."""

    PVSYST_CELL = "PVSystCell"


@dataclass(init=False, slots=True)
class CellTemperature:
    """CellTemperature."""

    cell_temperature: StringMetTimeSeries

    def __init__(
        self,
        *,
        cell_temperature_model: ModelThermal,
        indeces: Indeces,
        egpoai: StringMetTimeSeries,
        temperature_ambient: MetTimeSeries,
        module_id_by_string: SystemSeries,
        module_efficiency: ModuleEquipmentSeries,
    ):
        """Calculate the cell temperature via PVsyst cell temperature model"""
        # --- CONSTANTS ---
        WIND_SPEED = 0.0  # m/s
        U_C = 29.0
        U_V = 0.0
        ALPHA = 0.9

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                egpoai,
                temperature_ambient,
                module_id_by_string,
                module_efficiency,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- FACTORIZE ---
        inputs = factorize(
            dataframe=inputs,
            columns=["ambient_temperature", "efficiency", "global"],
            rounding_precision=2,
        )

        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        match cell_temperature_model:
            case ModelThermal.PVSYST_CELL:
                cell_temp = pvlib.temperature.pvsyst_cell(
                    poa_global=unique_by_group["global"],
                    temp_air=unique_by_group["ambient_temperature"],
                    wind_speed=WIND_SPEED,
                    u_c=U_C,
                    u_v=U_V,
                    module_efficiency=unique_by_group["efficiency"],
                    alpha_absorption=ALPHA,
                )
            case _:
                raise ValueError("This thermal model has not been implemented")

        # Only allow dataframes with positional indices
        cell_temp = cell_temp.rename("cell_temp")
        cell_temp = cell_temp.reset_index()

        # --- MERGE ---
        outputs = pd.merge(
            left=inputs,
            right=cell_temp,
            on="_unique_id",
            how="inner",
        )

        self.cell_temperature = StringMetTimeSeries(outputs.loc[:, "cell_temp"])
