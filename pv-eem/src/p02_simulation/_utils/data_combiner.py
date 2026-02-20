import logging
from collections.abc import Sequence
from enum import StrEnum

import pandas as pd
from interfaces import (
    CombinerDeviceSeries,
    CombinerTimeSeries,
    Indeces,
    InverterDeviceSeries,
    InverterEquipmentSeries,
    InverterTimeSeries,
    MetTimeSeries,
    ModuleEquipmentSeries,
    RackingEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
    TimeSeries,
    TransformerDeviceSeries,
    TransformerTimeSeries,
)

logger = logging.getLogger(__name__)

MergeableFrame = pd.Series | pd.DataFrame


class MergeHow(StrEnum):
    LEFT = "left"
    CROSS = "cross"
    INNER = "inner"


def merge_by_dimension(
    *,
    data_series: list[
        Indeces
        | TimeSeries
        | MetTimeSeries
        | StringMetTimeSeries
        | SystemSeries
        | ModuleEquipmentSeries
        | RackingEquipmentSeries
        | InverterEquipmentSeries
        | CombinerDeviceSeries
        | InverterDeviceSeries
        | TransformerDeviceSeries
        | CombinerTimeSeries
        | InverterTimeSeries
        | TransformerTimeSeries
    ],
    merge_how: MergeHow,
    indeces: Indeces,
    debug: bool = False,
) -> pd.DataFrame:
    # Initialize empty lists for each type of data
    time_columns: list[TimeSeries | pd.Series] = []
    time_met_columns: list[MetTimeSeries | pd.DataFrame] = []
    time_met_string_columns: list[StringMetTimeSeries | pd.DataFrame] = []
    system_columns: list[SystemSeries | pd.Series] = []
    module_equipment_columns: list[ModuleEquipmentSeries | pd.Series] = []
    racking_equipment_columns: list[RackingEquipmentSeries | pd.Series] = []
    inverter_equipment_columns: list[InverterEquipmentSeries | pd.Series] = []
    combiner_device_columns: list[SystemSeries | CombinerDeviceSeries | pd.Series] = []
    inverter_device_columns: list[InverterDeviceSeries | pd.Series] = []
    transformer_device_columns: list[TransformerDeviceSeries | pd.Series] = []
    combiner_time_columns: list[CombinerTimeSeries | pd.DataFrame] = []
    inverter_time_columns: list[InverterTimeSeries | pd.DataFrame] = []
    transformer_time_columns: list[TransformerTimeSeries | pd.DataFrame] = []

    # Add indeces
    time_columns.append(indeces.time_index)
    time_met_columns.append(indeces.met_time_index)
    time_met_string_columns.append(indeces.string_met_time_index)
    system_columns.append(indeces.string_index)
    module_equipment_columns.append(indeces.module_equipment_index)
    racking_equipment_columns.append(indeces.racking_equipment_index)
    inverter_equipment_columns.append(indeces.inverter_equipment_index)
    combiner_device_columns.append(indeces.combiner_device_index)
    inverter_device_columns.append(indeces.inverter_device_index)
    transformer_device_columns.append(indeces.transformer_device_index)
    combiner_time_columns.append(indeces.combiner_time_index)
    inverter_time_columns.append(indeces.inverter_time_index)
    transformer_time_columns.append(indeces.transformer_time_index)

    # Aggregate data by what dimensions that they are indexed by
    # Match statements here will cause a bug (python match is not implemented well)
    for series in data_series:
        if type(series) == TimeSeries:
            time_columns.append(series)
        elif type(series) == MetTimeSeries:
            time_met_columns.append(series)
        elif type(series) == StringMetTimeSeries:
            time_met_string_columns.append(series)
        elif type(series) == SystemSeries:
            system_columns.append(series)
        elif type(series) == ModuleEquipmentSeries:
            module_equipment_columns.append(series)
        elif type(series) == RackingEquipmentSeries:
            racking_equipment_columns.append(series)
        elif type(series) == InverterEquipmentSeries:
            inverter_equipment_columns.append(series)
        elif type(series) == CombinerDeviceSeries:
            combiner_device_columns.append(series)
        elif type(series) == InverterDeviceSeries:
            inverter_device_columns.append(series)
        elif type(series) == TransformerDeviceSeries:
            transformer_device_columns.append(series)
        elif type(series) == CombinerTimeSeries:
            combiner_time_columns.append(series)
        elif type(series) == InverterTimeSeries:
            inverter_time_columns.append(series)
        elif type(series) == TransformerTimeSeries:
            transformer_time_columns.append(series)
        else:
            raise TypeError("Wrong Type in data combiner")

    def merge_columns(
        *,
        merge_how: MergeHow,
        left: pd.DataFrame | None,
        right: Sequence[MergeableFrame],
        on: list[str],
        debug: bool = False,
    ) -> pd.DataFrame | None:
        """Helper function to merge columns with the main dataframe"""
        # Nothing to merge in, just the index
        if len(right) <= 1:
            return left

        right_df: pd.DataFrame = pd.concat(right, axis=1)
        if left is None:
            return right_df
        else:
            if debug:
                logger.info("Pause here with debugger")

            return pd.merge(
                left=left,
                right=right_df,
                on=on,
                how=merge_how.value,
            )

    # Merge dataframes in order of dimensionality (most specific to least specific)
    df = None

    # Define merge operations in order
    # ORDER IS IMPORTANT HERE SINCE MOST OPERATIONS ARE MERGE LEFT
    merge_operations: list[tuple[Sequence[MergeableFrame], list[str]]] = [
        (transformer_time_columns, ["transformer_device_id", "time"]),
        (inverter_time_columns, ["inverter_device_id", "time"]),
        (combiner_time_columns, ["combiner_device_id", "time"]),
        (transformer_device_columns, ["transformer_device_id"]),
        (inverter_device_columns, ["pcs_device_id"]),
        (combiner_device_columns, ["combiner_device_id"]),
        (time_met_string_columns, ["time", "met_name", "string_id"]),
        (time_met_columns, ["time", "met_name"]),
        (time_columns, ["time"]),
        (system_columns, ["string_id"]),
        (module_equipment_columns, ["module_equipment_id"]),
        (racking_equipment_columns, ["racking_equipment_id"]),
        (inverter_equipment_columns, ["inverter_equipment_id"]),
    ]

    # Perform all merges
    for columns, merge_keys in merge_operations:
        df = merge_columns(
            left=df,
            right=columns,
            on=merge_keys,
            merge_how=merge_how,
            debug=debug,
        )

    if df is None:
        raise ValueError("No data to merge")

    return df
