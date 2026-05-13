import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import TimeCoord


def solv_is_sunny(
    *,
    irradiance: xr.DataArray,
) -> xr.DataArray:
    SOLAR_IRRADIANCE_POA_THRESHOLD_W_M2 = 85
    return irradiance > SOLAR_IRRADIANCE_POA_THRESHOLD_W_M2


def solv_period_produced(
    *,
    irradiance: xr.DataArray,
    power: xr.DataArray,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    is_sunny = solv_is_sunny(irradiance=irradiance)
    project_meter_energy_mwh = power / 12
    return (
        project_meter_energy_mwh.where(is_sunny)
        .groupby(date_local_5m)
        .sum(min_count=1)
    )


def solv_lost_period(
    *,
    irradiance: xr.DataArray,
    unit_ac_power: xr.DataArray,
    unit_power_setpoint: xr.DataArray,
    power: xr.DataArray,
    unit_ac_capacity: xr.DataArray,
    unit_dc_capacity: xr.DataArray,
    expected_energy: xr.DataArray,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    ##
    # Define constants
    #

    CLIPPING_THRESHOLD = 0.99
    NORMALIZED_THRESHOLD_FOR_NO_POWER = 0.001
    DERATED_THRESHOLD = 0.90
    WINDOW_SIZE_FOR_DERATED_THRESHOLD = 12

    is_sunny = solv_is_sunny(irradiance=irradiance)

    ##
    # Calculate the Period MWh Lost
    # This is a multi-step process
    #

    # Step 1: For Off-line Units

    # Scale unit power so the sum matches project meter power.
    revised_unit_kw = (
        unit_ac_power
        / unit_ac_power.sum(dim=DeviceTypeEnum.PV_INVERTER.name.lower())
        * power
    )
    # Contract also uses current vs setpoint for clipping; setpoint was unavailable.
    unit_is_clipping_5m = unit_ac_power > unit_power_setpoint * CLIPPING_THRESHOLD
    unit_ac_or_dc_capacity_kw_5m = xr.where(
        unit_is_clipping_5m, unit_ac_capacity, unit_dc_capacity
    )
    project_average_of_all_units_ac_or_dc_capacity_kw_5m = (
        unit_ac_or_dc_capacity_kw_5m.mean(dim=DeviceTypeEnum.PV_INVERTER.name.lower())
    )
    normalized_unit_kw = (
        revised_unit_kw
        * project_average_of_all_units_ac_or_dc_capacity_kw_5m
        / unit_ac_or_dc_capacity_kw_5m
    )
    norm_p80 = normalized_unit_kw.quantile(
        dim=DeviceTypeEnum.PV_INVERTER.name.lower(), q=0.8
    ).drop("quantile")
    average_unit_nv = normalized_unit_kw.where(normalized_unit_kw > norm_p80).mean(
        dim=DeviceTypeEnum.PV_INVERTER.name.lower()
    )
    unit_power_lost_when_offline_kw_5m = (
        average_unit_nv
        * unit_ac_or_dc_capacity_kw_5m
        / project_average_of_all_units_ac_or_dc_capacity_kw_5m
    )

    unit_energy_lost_when_offline_kwh_5m = unit_power_lost_when_offline_kw_5m / 12

    unit_is_offline = (
        unit_ac_power < NORMALIZED_THRESHOLD_FOR_NO_POWER * unit_ac_capacity
    )

    # Step 2: For Derated Units

    unit_energy_lost_when_derated_kwh_5m = (
        average_unit_nv
        * unit_ac_or_dc_capacity_kw_5m
        / project_average_of_all_units_ac_or_dc_capacity_kw_5m
        - revised_unit_kw
    ) / 12

    meets_derated_threshold = normalized_unit_kw <= (
        DERATED_THRESHOLD * average_unit_nv
    )
    previous_hour_meets_threshold = meets_derated_threshold.rolling(
        {TimeCoord.TIME_5MIN_UTC.value: WINDOW_SIZE_FOR_DERATED_THRESHOLD}
    ).min()
    unit_is_derated_5m = (
        previous_hour_meets_threshold.rolling(
            {TimeCoord.TIME_5MIN_UTC.value: WINDOW_SIZE_FOR_DERATED_THRESHOLD}
        )
        .max()
        .shift(
            {TimeCoord.TIME_5MIN_UTC.value: -(WINDOW_SIZE_FOR_DERATED_THRESHOLD - 1)}
        )
    )
    unit_is_derated_5m = unit_is_derated_5m.astype(bool)

    # Step 3: For Facility Offline

    facility_is_offline = unit_is_offline.all(
        dim=DeviceTypeEnum.PV_INVERTER.name.lower()
    )

    ## Expected energy model language in the contract is specific; we lack the
    # month-of-year initial model and use our internal expected energy instead.

    # For now, this is a placeholder that always returns False.
    is_excuse_event = xr.DataArray(False)

    # from all components

    # at the Unit/PCS level

    unit_energy_lost_kwh_5m = xr.where(
        unit_is_offline,
        unit_energy_lost_when_offline_kwh_5m,
        xr.where(
            unit_is_derated_5m,
            unit_energy_lost_when_derated_kwh_5m,
            0,
        ),
    )

    project_energy_lost_kwh_5m = unit_energy_lost_kwh_5m.sum(
        dim=DeviceTypeEnum.PV_INVERTER.name.lower()
    )

    # at the facility level

    project_energy_lost_kwh_5m = xr.where(
        ~is_sunny | is_excuse_event,
        0,
        xr.where(
            facility_is_offline,
            expected_energy,
            project_energy_lost_kwh_5m,
        ),
    )

    # The sum result

    period_kwh_lost = project_energy_lost_kwh_5m.groupby(date_local_5m).sum(
        min_count=1
    )

    return period_kwh_lost
