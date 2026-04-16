from dataclasses import dataclass

import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs, TimeCoords
from kpi.domain.util import daily_mean_across_devices, diff, filter_mask
from kpi.infra.pvlib_integration import theoretical_poa_irradiance
from kpi.service.util import select_optional, select_var


@dataclass
class DailyMeanAcrossDevices:
    """
    This is an example. I would use these kinds of classes sparingly.
    I prefer the functional approach to just directly use daily_mean_across_devices.
    """

    value: str
    date_local_5m: str
    device_type: DeviceType

    def inputs(self) -> set[str]:
        return {self.value, self.date_local_5m}

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return daily_mean_across_devices(
            value=select_var(dataset, self.value),
            device_type=self.device_type,
            date_local_5m=select_var(dataset, self.date_local_5m),
        )


@dataclass
class TheoreticalPoaIrradiance:
    project_latitude_deg: str
    project_longitude_deg: str
    project_elevation_m: str

    def inputs(self) -> set[str]:
        return {
            self.project_latitude_deg,
            self.project_longitude_deg,
            self.project_elevation_m,
        }

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return theoretical_poa_irradiance(
            time_utc=pd.DatetimeIndex(
                dataset.coords[TimeCoords.TIME_5MIN_UTC.value].values
            ),
            latitude=select_var(dataset, self.project_latitude_deg).item(),
            longitude=select_var(dataset, self.project_longitude_deg).item(),
            elevation=select_optional(dataset, self.project_elevation_m),
            time_zone=dataset.attrs[Attrs.TIME_ZONE.value],
            project_name_short=dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
        )


@dataclass
class Energy5mFromAccumulator:
    """
    Compute the incremental 5-minute difference from each step
    of the energy accumulator. Since energy accumulators should be
    increasing, any downward steps are removed. Likewise,
    energy cannot exceed the hourly rate given by its power capacity,
    so any 5-minute period with a positive jump of more than one twelfth
    of the power capacity is removed. This removes any catch-up jumps
    that might occur after a telemetry gap.
    """

    accumulator: str
    power_capacity: str

    def inputs(self) -> set[str]:
        return {self.accumulator, self.power_capacity}

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        difference = diff(select_var(dataset, self.accumulator))
        epsilon = 1e-6
        clean_diff = difference.where(
            filter_mask(
                filter_by=difference / select_var(dataset, self.power_capacity),
                min_value=-epsilon,
                max_value=1 / 12 + epsilon,
            )
        )
        return clean_diff
