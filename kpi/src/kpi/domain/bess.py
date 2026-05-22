"""Battery energy storage system (BESS) domain helpers.

Functions operate on ``xarray.DataArray`` inputs for SOC, SOH, power, energy,
and related signals used in KPI transforms.
"""

import xarray as xr

from kpi.base.enumeration import TimeCoord
from kpi.domain.agg.resample import resample_sum
from kpi.domain.util import cumsum, diff, filter_mask


def clean_soc(soc: xr.DataArray) -> xr.DataArray:
    """Mask SOC values outside a small positive band below 1.

    Args:
        soc: State of charge, dimensionless in ``(0, 1]``.

    Returns:
        ``soc`` with values outside ``(1e-6, 1]`` set to NaN.
    """
    epsilon = 1e-6
    return soc.where(filter_mask(filter_by=soc, min_value=epsilon, max_value=1))


def clean_soh(soh: xr.DataArray) -> xr.DataArray:
    """Mask state-of-health values outside ``[0.2, 1]``.

    Args:
        soh: State of health, dimensionless.

    Returns:
        ``soh`` with values outside ``[0.2, 1]`` set to NaN.
    """
    return soh.where(filter_mask(filter_by=soh, min_value=0.2, max_value=1))


def clean_temperature(temp_c: xr.DataArray) -> xr.DataArray:
    """Mask implausible cell or pack temperatures in Celsius.

    Args:
        temp_c: Temperature in degrees Celsius.

    Returns:
        ``temp_c`` with values outside ``[1, 150]`` set to NaN.
    """
    return temp_c.where(filter_mask(filter_by=temp_c, min_value=1, max_value=150))


def clean_cell_voltage(voltage: xr.DataArray) -> xr.DataArray:
    """Mask cell voltages outside a plausible per-cell range.

    Args:
        voltage: Cell voltage in volts.

    Returns:
        ``voltage`` with values outside ``(-1e-6, 8]`` set to NaN.
    """
    return voltage.where(filter_mask(filter_by=voltage, min_value=-1e-6, max_value=8))


def clean_power(
    *,
    power: xr.DataArray,
    capacity: xr.DataArray,
) -> xr.DataArray:
    """Mask power where normalized magnitude exceeds one (with epsilon slack).

    Args:
        power: Electrical power (same units as implied by ``capacity`` rate).
        capacity: Energy capacity used to normalize ``power`` to per-unit C-rate
            magnitude.

    Returns:
        ``power`` where ``|power / capacity|`` is outside ``[-1-eps, 1+eps]`` set
        to NaN.
    """
    epsilon = 1e-6
    return power.where(
        filter_mask(
            filter_by=power / capacity,
            min_value=-1 - epsilon,
            max_value=1 + epsilon,
        )
    )


def resting_soc(soc: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    """Keep SOC points where the absolute step change is below a threshold.

    Args:
        soc: State of charge time series.
        threshold: Maximum absolute first difference to treat as "resting".

    Returns:
        ``soc`` where ``|diff(soc)| < threshold``; elsewhere NaN.
    """
    difference = abs(diff(soc))
    return soc.where(difference < threshold)


def cycle_count(*, soc: xr.DataArray, grouper: xr.DataArray) -> xr.DataArray:
    """Half-cycle count from SOC changes, aggregated by ``grouper``.

    Args:
        soc: State of charge time series.
        grouper: Coordinate or array used to group before summing (e.g. local date).

    Returns:
        Sum of ``|diff(soc)| / 2`` within each group of ``grouper``.
    """
    cycle_abs = abs(diff(soc)) / 2
    return resample_sum(cycle_abs, grouper=grouper)


def soc_balance_score(soc_var: xr.DataArray) -> xr.DataArray:
    """Map SOC variance to a simple balance score in ``(-inf, 1]``.

    Args:
        soc_var: Variance of state of charge (or related spread measure).

    Returns:
        ``1 - 2 * sqrt(soc_var)``.
    """
    sigma = soc_var**0.5
    return 1 - 2 * sigma


def is_charging(c_rate: xr.DataArray) -> xr.DataArray:
    """Boolean mask for charging (negative C-rate below a small threshold).

    Args:
        c_rate: Normalized current or power (positive = discharge).

    Returns:
        DataArray of booleans, true where ``c_rate < -0.01``.
    """
    return c_rate < -0.01


def is_discharging(c_rate: xr.DataArray) -> xr.DataArray:
    """Boolean mask for discharging (positive C-rate above a small threshold).

    Args:
        c_rate: Normalized current or power (positive = discharge).

    Returns:
        DataArray of booleans, true where ``c_rate > 0.01``.
    """
    return c_rate > 0.01


def is_idling(c_rate: xr.DataArray) -> xr.DataArray:
    """Boolean mask for near-zero C-rate (neither charging nor discharging).

    Args:
        c_rate: Normalized current or power.

    Returns:
        DataArray of booleans, true where ``-0.01 < c_rate < 0.01``.
    """
    return (c_rate < 0.01) & (c_rate > -0.01)


def maximum_continuous_discharged_energy(
    *,
    discharge_energy: xr.DataArray,
    charge_energy: xr.DataArray,
    date_local_5m: xr.DataArray,
    energy_capacity: xr.DataArray | None = None,
) -> xr.DataArray:
    """Maximum energy discharged in one continuous discharge segment per local day.

    If a day has multiple discharge periods, the largest continuous discharge total
    is used. Segments that cross midnight are split: energy up to midnight counts
    toward the previous day; the remainder counts toward the next day.

    Args:
        discharge_energy: Incremental discharge energy per timestep.
        charge_energy: Incremental charge energy per timestep (resets baseline).
        date_local_5m: Local date label aligned to 5-minute grid for grouping.
        energy_capacity: If set, masks totals where normalized discharge exceeds
            one.

    Returns:
        Per-day maximum of cumulative discharge since the last charge, grouped by
        ``date_local_5m``.
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

    return result.groupby(date_local_5m).max()


def bess_filter_daily_energy(
    *,
    energy_unfiltered_d: xr.DataArray,
    energy_capacity: xr.DataArray,
    max_cycles: float = 3,
) -> xr.DataArray:
    """Drop daily energy totals that are negative or exceed ``max_cycles`` capacity.

    Args:
        energy_unfiltered_d: Daily energy total (same energy units as capacity).
        energy_capacity: Nameplate or reference energy capacity for normalization.
        max_cycles: Upper bound on acceptable ``energy / capacity`` (cycles).

    Returns:
        ``energy_unfiltered_d`` with invalid ratios masked to NaN.
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
    """Instantaneous C-rate from power and energy capacity.

    Args:
        power: Power (consistent with energy capacity rate, e.g. W vs Wh).
        energy_capacity: Stored energy capacity.

    Returns:
        ``power / energy_capacity``.
    """
    return power / energy_capacity


def energy_efficiency(
    source: xr.DataArray,
    sink: xr.DataArray,
    energy_capacity: xr.DataArray,
) -> xr.DataArray:
    """Ratio of output energy to input energy, excluding low-source days.

    Days where source energy is below 10% of ``energy_capacity`` are excluded
    (masked). Resulting efficiency is clipped to ``[0, 1 + eps]``.

    Args:
        source: Input-side cumulative or interval energy.
        sink: Output-side cumulative or interval energy.
        energy_capacity: Capacity used to filter low-source periods and clip.

    Returns:
        ``sink / source`` for points passing the source threshold and efficiency
        bounds.
    """
    source_filtered = source.where(source / energy_capacity > 0.1)
    efficiency = sink / source_filtered
    epsilon = 1e-6
    return efficiency.where(
        filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
    )


def depth_of_discharge(soc: xr.DataArray) -> xr.DataArray:
    """Depth of discharge as one minus state of charge.

    Args:
        soc: State of charge in ``[0, 1]`` (or masked outside).

    Returns:
        ``1 - soc``.
    """
    return 1 - soc


def c_rate_while_charging(c_rate: xr.DataArray) -> xr.DataArray:
    """Positive magnitude of C-rate during charging only.

    Args:
        c_rate: Signed C-rate (negative while charging).

    Returns:
        ``-c_rate`` where ``is_charging(c_rate)``; else NaN.
    """
    return -c_rate.where(is_charging(c_rate))


def perfect_availability_intervals(
    availability_5m: xr.DataArray,
    *,
    epsilon: float = 1e-6,
) -> xr.DataArray:
    """Map 5-minute availability to perfect (1), imperfect (0), or missing (NaN).

    Shared by daily and hourly NER availability registry fields.

    Args:
        availability_5m: Fractional availability at 5-minute resolution.
        epsilon: Tolerance below 1.0 treated as perfect.

    Returns:
        ``1.0``, ``0.0``, or NaN per interval.
    """
    return xr.where(
        availability_5m >= 1 - epsilon,
        1.0,
        xr.where(availability_5m < 1 - epsilon, 0.0, float("nan")),
    )


def c_rate_while_discharging(c_rate: xr.DataArray) -> xr.DataArray:
    """C-rate during discharging only.

    Args:
        c_rate: Signed C-rate (positive while discharging).

    Returns:
        ``c_rate`` where ``is_discharging(c_rate)``; else NaN.
    """
    return c_rate.where(is_discharging(c_rate))
