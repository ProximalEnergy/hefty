import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs, TimeCoords
from kpi.domain.util import daily_mean_across_devices, date_local, diff, filter_mask
from kpi.infra.pvlib_integration import theoretical_poa_irradiance
from kpi.op.transform.input import InputType, Optional, Required
from pydantic import BaseModel


class BaseCalc(BaseModel):
    def inputs(self) -> set[str]:
        input_set = set[str]()
        for name in type(self).model_fields.keys():
            instance = getattr(self, name)
            if isinstance(instance, InputType):
                input_set.add(instance.name)
        return input_set


class DailyMeanAcrossDevices(BaseCalc):
    """
    This is an example. I would use these kinds of classes sparingly.
    I prefer the functional approach to just directly use daily_mean_across_devices.
    """

    value: Required
    date_local_5m: Required
    device_type: DeviceType

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return daily_mean_across_devices(
            value=self.value.get(dataset),
            device_type=self.device_type,
            date_local_5m=self.date_local_5m.get(dataset),
        )


class TheoreticalPoaIrradiance(BaseCalc):
    project_latitude_deg: Required
    project_longitude_deg: Required
    project_elevation_m: Optional

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return theoretical_poa_irradiance(
            time_utc=pd.DatetimeIndex(
                dataset.coords[TimeCoords.TIME_5MIN_UTC.value].values
            ),
            latitude=self.project_latitude_deg.get(dataset).item(),
            longitude=self.project_longitude_deg.get(dataset).item(),
            elevation=self.project_elevation_m.get(dataset),
            time_zone=dataset.attrs[Attrs.TIME_ZONE.value],
            project_name_short=dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
        )


class Energy5mFromAccumulator(BaseCalc):
    """
    Compute the incremental 5-minute difference from each step
    of the energy accumulator. Since energy accumulators should be
    increasing, any downward steps are removed. Likewise,
    energy cannot exceed the hourly rate given by its power capacity,
    so any 5-minute period with a positive jump of more than one twelfth
    of the power capacity is removed. This removes any catch-up jumps
    that might occur after a telemetry gap.
    """

    accumulator: Required
    power_capacity: Required

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        difference = diff(self.accumulator.get(dataset))
        epsilon = 1e-6
        clean_diff = difference.where(
            filter_mask(
                filter_by=difference / self.power_capacity.get(dataset),
                min_value=-epsilon,
                max_value=1 / 12 + epsilon,
            )
        )
        return clean_diff


class DailyEnergy(BaseCalc):
    """
    Compute daily energy from an 5-minute increasing energy accumulator.
    Each day's energy is the difference in the accumulator's value from midnight to
    midnight the next day. This ensures that even if there are telemetry gaps
    in the middle of the day or strange jumps that resolve themselves, the daily
    total is not affected.
    However, if the total energy is negative or greater than 3 times the energy capacity
    of that device, it is considered invalid and thrown out since this
    would indicate 3 full cycles in a single day which is very unlikely.
    If the accumulator has a wrap-around value, it is provided and the energy total
    is considered as the mod difference to correctly account for days that start
    at the high end of the accumulator's range and reset during the middle of the day.
    """

    total_energy_5m: Required
    date_local_5m: Required
    energy_capacity: Required
    max_cycles: float = 3
    modulus: float | None = None

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        grouper = date_local(self.date_local_5m.get(dataset))
        total_energy_d = self.total_energy_5m.get(dataset).groupby(grouper).first()
        difference = diff(total_energy_d, time_dim=TimeCoords.DATE_LOCAL)
        epsilon = 1e-6
        if self.modulus is not None:
            difference = ((difference + epsilon) % self.modulus) - epsilon
        difference = difference.where(
            filter_mask(
                filter_by=difference / self.energy_capacity.get(dataset),
                min_value=-epsilon,
                max_value=self.max_cycles,
            )
        )
        return difference
