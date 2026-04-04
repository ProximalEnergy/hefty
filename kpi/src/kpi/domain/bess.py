import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.domain.util import date_local, diff, filter_mask


def clean_soc(soc: xr.DataArray) -> xr.DataArray:
    epsilon = 1e-6
    return soc.where(filter_mask(filter_by=soc, min_value=epsilon, max_value=1))


def clean_soh(soh: xr.DataArray) -> xr.DataArray:
    return soh.where(filter_mask(filter_by=soh, min_value=0.2, max_value=1))


def clean_temperature(temp_c: xr.DataArray) -> xr.DataArray:
    return temp_c.where(filter_mask(filter_by=temp_c, min_value=1, max_value=150))


def clean_cell_voltage(voltage: xr.DataArray) -> xr.DataArray:
    return voltage.where(filter_mask(filter_by=voltage, min_value=-1e-6, max_value=8))


def resting_soc(soc: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    difference = abs(diff(soc))
    return soc.where(difference < threshold)


def cycle_count(*, soc: xr.DataArray, grouper: xr.DataArray) -> xr.DataArray:
    cycle_abs = abs(diff(soc)) / 2
    return cycle_abs.groupby(grouper).sum()


def soc_balance_score(soc_var: xr.DataArray) -> xr.DataArray:
    sigma = soc_var**0.5
    return 1 - 2 * sigma


def daily_energy(
    *,
    total_energy_5m: xr.DataArray,
    power_capacity: xr.DataArray,
    date_local_5m: xr.DataArray,
    max_capacity_factor: float = 12,
    modulus: float | None = None,
) -> xr.DataArray:
    total_energy_d = total_energy_5m.groupby(date_local(date_local_5m)).first()
    difference = diff(total_energy_d, time_dim=TimeCoords.DATE_LOCAL)
    epsilon = 1e-6
    if modulus is not None:
        difference = ((difference + epsilon) % modulus) - epsilon
    return difference.where(
        filter_mask(
            filter_by=difference / power_capacity,
            min_value=-epsilon,
            max_value=max_capacity_factor + epsilon,
        )
    )


def is_charging(c_rate: xr.DataArray) -> xr.DataArray:
    return c_rate < -0.01


def is_discharging(c_rate: xr.DataArray) -> xr.DataArray:
    return c_rate > 0.01


def is_idling(c_rate: xr.DataArray) -> xr.DataArray:
    return (c_rate < 0.01) & (c_rate > -0.01)
