import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.domain.util import daily_mean_across_devices, date_local, diff, filter_mask
from kpi.infra.pvlib_integration import theoretical_poa_irradiance
from kpi.op.context import get_context
from kpi.op.transform.input import InputType, Optional, Required
from pydantic import BaseModel, ConfigDict


class BaseCalc(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

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
            value=self.value.extract(dataset),
            device_type=self.device_type,
            date_local_5m=self.date_local_5m.extract(dataset),
        )


class TheoreticalPoaIrradiance(BaseCalc):
    project_latitude_deg: Required
    project_longitude_deg: Required
    project_elevation_m: Optional

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        context = get_context(dataset)
        return theoretical_poa_irradiance(
            time_utc=pd.DatetimeIndex(
                dataset.coords[TimeCoords.TIME_5MIN_UTC.value].values
            ),
            latitude=self.project_latitude_deg.extract(dataset).item(),
            longitude=self.project_longitude_deg.extract(dataset).item(),
            elevation=self.project_elevation_m.extract(dataset),
            time_zone=context.time_zone,
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
        difference = diff(self.accumulator.extract(dataset))
        epsilon = 1e-6
        clean_diff = difference.where(
            filter_mask(
                filter_by=difference / self.power_capacity.extract(dataset),
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

    # inputs
    total_energy_5m: Required
    date_local_5m: Required
    energy_capacity: Required

    # other parameters
    max_cycles: float = 3
    modulus: float | None = None

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        # get variables from inputs
        date_local_5m = self.date_local_5m.extract(dataset)
        total_energy_5m = self.total_energy_5m.extract(dataset)
        energy_capacity = self.energy_capacity.extract(dataset)

        # perform calculation
        total_energy_d = total_energy_5m.groupby(date_local(date_local_5m)).first()
        difference = diff(total_energy_d, time_dim=TimeCoords.DATE_LOCAL)
        epsilon = 1e-6
        if self.modulus is not None:
            difference = ((difference + epsilon) % self.modulus) - epsilon
        difference = difference.where(
            filter_mask(
                filter_by=difference / energy_capacity,
                min_value=-epsilon,
                max_value=self.max_cycles,
            )
        )
        return difference


class Event(BaseCalc):
    """
    Calculates whether the 5-minute interval is in an event.
    The `event_change` parameter is the number of events that began
    minus the number of events that ended in the 5-minute interval.
    It's assumed that every event has a start and end within the entire
    period. Events that began before the start date should have been counted
    as starting on the first time step, and events that finished after
    the end date should have been counted as ending on the last time step.
    This calculation does a forward cumulative sum to effectively determine
    the number of events that are active for each point in time.
    Intervals where the cumulative sum is greater than 0 are in an event and
    result in True, and intervals where the cumulative sum is 0 are not in an event
    and result in False.
    """

    event_change: Required

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        event_change = self.event_change.extract(dataset)
        return event_change.cumsum(dim=TimeCoords.TIME_5MIN_UTC.value) > 0


class BessCleanPower(BaseCalc):
    """
    Clean power by capacity.
    Exclude power values that exceed the capacity in the positive or negative direction.
    """

    power: Required
    capacity: Required

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        power = self.power.extract(dataset)
        capacity = self.capacity.extract(dataset)

        epsilon = 1e-6
        return power.where(
            filter_mask(
                filter_by=power / capacity,
                min_value=-1 - epsilon,
                max_value=1 + epsilon,
            )
        )
