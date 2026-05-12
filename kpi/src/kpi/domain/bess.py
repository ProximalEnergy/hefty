import xarray as xr
from kpi.base.enumeration import TimeCoord
from kpi.domain.agg.resample import resample_sum
from kpi.domain.util import cumsum, diff, filter_mask, rename


def clean_soc(soc: xr.DataArray) -> xr.DataArray:
    epsilon = 1e-6
    return soc.where(filter_mask(filter_by=soc, min_value=epsilon, max_value=1))


def clean_soh(soh: xr.DataArray) -> xr.DataArray:
    return soh.where(filter_mask(filter_by=soh, min_value=0.2, max_value=1))


def clean_temperature(temp_c: xr.DataArray) -> xr.DataArray:
    return temp_c.where(filter_mask(filter_by=temp_c, min_value=1, max_value=150))


def clean_cell_voltage(voltage: xr.DataArray) -> xr.DataArray:
    return voltage.where(filter_mask(filter_by=voltage, min_value=-1e-6, max_value=8))


def clean_power(
    *,
    power: xr.DataArray,
    capacity: xr.DataArray,
) -> xr.DataArray:
    epsilon = 1e-6
    return power.where(
        filter_mask(
            filter_by=power / capacity,
            min_value=-1 - epsilon,
            max_value=1 + epsilon,
        )
    )


def resting_soc(soc: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    difference = abs(diff(soc))
    return soc.where(difference < threshold)


def cycle_count(*, soc: xr.DataArray, grouper: xr.DataArray) -> xr.DataArray:
    cycle_abs = abs(diff(soc)) / 2
    return resample_sum(cycle_abs, grouper=grouper)


def soc_balance_score(soc_var: xr.DataArray) -> xr.DataArray:
    sigma = soc_var**0.5
    return 1 - 2 * sigma


def is_charging(c_rate: xr.DataArray) -> xr.DataArray:
    return c_rate < -0.01


def is_discharging(c_rate: xr.DataArray) -> xr.DataArray:
    return c_rate > 0.01


def is_idling(c_rate: xr.DataArray) -> xr.DataArray:
    return (c_rate < 0.01) & (c_rate > -0.01)


def maximum_continuous_discharged_energy(
    *,
    discharge_energy: xr.DataArray,
    charge_energy: xr.DataArray,
    date_local_5m: xr.DataArray,
    energy_capacity: xr.DataArray | None = None,
) -> xr.DataArray:
    """
    The maximum amount of energy that was discharged in a continuous period.
    If a day has multiple discharging periods, the highest energy period is used.
    Discharging events that straddle midnight are counted in part (up to midnight)
    on the previous day and in whole on the next day.
    """

    discharge_total = cumsum(discharge_energy)

    is_charging = charge_energy > 1e-6

    discharge_total_while_charging = discharge_total.where(is_charging)

    # determine a baseline total from the most recent charging event
    total_discharged_since_last_charging = discharge_total_while_charging.ffill(
        dim=TimeCoord.TIME_5MIN_UTC.value
    )

    result = discharge_total - total_discharged_since_last_charging

    # make sure the total discharged is not greater than the energy capacity
    if energy_capacity is not None:
        result = result.where(
            filter_mask(
                filter_by=result / energy_capacity,
                min_value=0,
                max_value=1,
            )
        )

    return result.groupby(rename(date_local_5m)).max()


def bess_filter_daily_energy(
    *,
    energy_unfiltered_d: xr.DataArray,
    energy_capacity: xr.DataArray,
    max_cycles: float = 3,
) -> xr.DataArray:
    """
    Reject daily energy totals that are negative or exceed the maximum number of cycles.
    """
    epsilon = 1e-6
    return energy_unfiltered_d.where(
        filter_mask(
            filter_by=energy_unfiltered_d / energy_capacity,
            min_value=-epsilon,
            max_value=max_cycles,
        )
    )


def c_rate(
    *,
    power: xr.DataArray,
    energy_capacity: xr.DataArray,
) -> xr.DataArray:
    return power / energy_capacity


def energy_efficiency(
    source: xr.DataArray,
    sink: xr.DataArray,
    energy_capacity: xr.DataArray,
) -> xr.DataArray:
    """
    Energy efficiency is the ratio of the energy output to the energy input.
    Days where the source energy is less than 10% of the energy capacity are excluded.
    """
    source_filtered = source.where(source / energy_capacity > 0.1)
    efficiency = sink / source_filtered
    epsilon = 1e-6
    return efficiency.where(
        filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
    )


def depth_of_discharge(soc: xr.DataArray) -> xr.DataArray:
    return 1 - soc


def c_rate_while_charging(c_rate: xr.DataArray) -> xr.DataArray:
    return -c_rate.where(is_charging(c_rate))


def c_rate_while_discharging(c_rate: xr.DataArray) -> xr.DataArray:
    return c_rate.where(is_discharging(c_rate))
