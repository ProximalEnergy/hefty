import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.domain.agg.resample import resample_first, resample_sum
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


def energy_5m_from_accumulator(
    *,
    accumulator: xr.DataArray,
    power_capacity: xr.DataArray,
) -> xr.DataArray:
    """
    Compute the incremental 5-minute difference from an energy accumulator.
    """
    difference = diff(accumulator)
    epsilon = 1e-6
    return difference.where(
        filter_mask(
            filter_by=difference / power_capacity,
            min_value=-epsilon,
            max_value=1 / 12 + epsilon,
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
        dim=TimeCoords.TIME_5MIN_UTC.value
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


def daily_energy(
    *,
    total_energy_5m: xr.DataArray,
    date_local_5m: xr.DataArray,
    energy_capacity: xr.DataArray,
    max_cycles: float = 3,
    modulus: float | None = None,
) -> xr.DataArray:
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
    total_energy_d = resample_first(total_energy_5m, grouper=date_local_5m)
    difference = diff(total_energy_d, time_dim=TimeCoords.DATE_LOCAL)
    epsilon = 1e-6
    if modulus is not None:
        difference = ((difference + epsilon) % modulus) - epsilon
    difference = difference.where(
        filter_mask(
            filter_by=difference / energy_capacity,
            min_value=-epsilon,
            max_value=max_cycles,
        )
    )
    return difference


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
