from dataclasses import dataclass
from typing import Annotated

import pandas as pd


# --- Primitive Series Types ---
# a time series only
class TimeSeries(pd.Series):
    """TimeSeries."""


# a timeseries for each met station
class MetTimeSeries(pd.Series):
    """MetTimeSeries."""


# a timeseries for each met station and each string
class StringMetTimeSeries(pd.Series):
    """StringMetTimeSeries."""


class CombinerTimeSeries(pd.Series):
    """CombinerTimeSeries."""


class InverterTimeSeries(pd.Series):
    """InverterTimeSeries."""


class TransformerTimeSeries(pd.Series):
    """TransformerTimeSeries."""


# --- System Series ---
# The system is a flat data-structure, these are the id's of the equipment
class SystemSeries(pd.Series):
    """SystemSeries."""


class CombinerDeviceSeries(pd.Series):
    """CombinerDeviceSeries."""


class InverterDeviceSeries(pd.Series):
    """InverterDeviceSeries."""


class TransformerDeviceSeries(pd.Series):
    """TransformerDeviceSeries."""


# Equipment Series
# The individual tables for a project's equipment modeling parameters
class ModuleEquipmentSeries(pd.Series):
    """ModuleEquipmentSeries."""


class InverterEquipmentSeries(pd.Series):
    """InverterEquipmentSeries."""


class RackingEquipmentSeries(pd.Series):
    """RackingEquipmentSeries."""


# --- Multi DimensionalIndexes ---
# A convenience dataframe index made up of primitives
class MetTimeIndex(pd.DataFrame):
    """MetTimeIndex."""


class StringMetTimeIndex(pd.DataFrame):
    """StringMetTimeIndex."""


class CombinerTimeIndex(pd.DataFrame):
    """CombinerTimeIndex."""


class InverterTimeIndex(pd.DataFrame):
    """InverterTimeIndex."""


class TransformerTimeIndex(pd.DataFrame):
    """TransformerTimeIndex."""


@dataclass(init=False, slots=True)
class Indeces:
    """Indeces."""

    time_index: TimeSeries
    met_time_index: MetTimeIndex
    string_met_time_index: StringMetTimeIndex
    combiner_time_index: CombinerTimeIndex
    inverter_time_index: InverterTimeIndex
    transformer_time_index: TransformerTimeIndex
    string_index: SystemSeries
    combiner_device_index: SystemSeries
    inverter_device_index: InverterDeviceSeries
    transformer_device_index: TransformerDeviceSeries
    module_equipment_index: ModuleEquipmentSeries
    racking_equipment_index: RackingEquipmentSeries
    inverter_equipment_index: InverterEquipmentSeries

    def __init__(
        self,
        *,
        met_time_index: MetTimeIndex,
        string_index: SystemSeries,
        module_equipment_index: ModuleEquipmentSeries,
        racking_equipment_index: RackingEquipmentSeries,
        inverter_equipment_index: InverterEquipmentSeries,
        combiner_device_index: SystemSeries,
        inverter_device_index: InverterDeviceSeries,
        transformer_device_index: TransformerDeviceSeries,
    ):
        # device indexes --> correspond with device_ids
        self.combiner_device_index = combiner_device_index
        self.inverter_device_index = inverter_device_index
        self.transformer_device_index = transformer_device_index

        # equipment indexes --> to merge with equipment modeling parameter tables
        self.string_index = string_index
        self.module_equipment_index = module_equipment_index
        self.racking_equipment_index = racking_equipment_index
        self.inverter_equipment_index = inverter_equipment_index

        # compute time index from met_time_index
        unique_by_group = met_time_index.groupby("time").first()
        self.time_index = TimeSeries(unique_by_group.index)
        self.met_time_index = MetTimeIndex(met_time_index)

        # These get assigned to later in the simulation
        self.string_met_time_index = StringMetTimeIndex(pd.Series())
        self.combiner_time_index = CombinerTimeIndex(pd.Series())
        self.inverter_time_index = InverterTimeIndex(pd.Series())
        self.transformer_time_index = TransformerTimeIndex(pd.Series())


# --- Other Classes ---
@dataclass(init=False, slots=True)
class QualityAssurance:
    """QualityAssurance."""

    tier: (
        MetTimeSeries
        | CombinerDeviceSeries
        | InverterTimeSeries
        | TransformerTimeSeries
    )
    tier_codes: (
        MetTimeSeries
        | CombinerDeviceSeries
        | InverterTimeSeries
        | TransformerTimeSeries
    )

    def __init__(
        self,
        *,
        tier: MetTimeSeries,
        tier_codes: MetTimeSeries,
    ):
        self.tier = tier
        self.tier_codes = tier_codes


@dataclass(init=False, slots=True)
class MetDataObserved:
    """MetDataObserved."""

    met_name: Annotated[MetTimeSeries, "String"]
    ambient_temperature: Annotated[MetTimeSeries, "°C"]
    ghi: Annotated[MetTimeSeries, "W/m²"]
    poa: Annotated[MetTimeSeries, "W/m²"]
    poa_tilt: Annotated[MetTimeSeries, "degrees"]
    relative_humidity: Annotated[MetTimeSeries, "% out of 100"]
    wind_speed: Annotated[MetTimeSeries, "m/s"]
    soil_percent: Annotated[MetTimeSeries, "% out of 1"]

    def __init__(self, *, met_data):
        self.met_name = MetTimeSeries(met_data.loc[:, "met_name"])
        self.ambient_temperature = MetTimeSeries(met_data.loc[:, "ambient_temperature"])
        self.ghi = MetTimeSeries(met_data.loc[:, "ghi"])
        self.poa = MetTimeSeries(met_data.loc[:, "poa"])
        self.poa_tilt = MetTimeSeries(met_data.loc[:, "poa_tilt"])
        self.relative_humidity = MetTimeSeries(met_data.loc[:, "relative_humidity"])
        self.wind_speed = MetTimeSeries(met_data.loc[:, "wind_speed"])
        self.soil_percent = MetTimeSeries(met_data.loc[:, "soil_percent"])
