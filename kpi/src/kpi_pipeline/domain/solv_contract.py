import xarray as xr
from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.protocols import CoordCombinerProtocol


def solv_is_sunny(
    *,
    project_irradiance_poa_w_m2_5m: xr.DataArray,
) -> xr.DataArray:
    SOLAR_IRRADIANCE_POA_THRESHOLD_W_M2 = 85
    return project_irradiance_poa_w_m2_5m > SOLAR_IRRADIANCE_POA_THRESHOLD_W_M2


def solv_period_kwh_produced(
    *,
    project_irradiance_poa_w_m2_5m: xr.DataArray,
    project_meter_power_kw_5m: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    is_sunny = solv_is_sunny(
        project_irradiance_poa_w_m2_5m=project_irradiance_poa_w_m2_5m
    )
    project_meter_energy_mwh = project_meter_power_kw_5m / 12
    return time_combiner.agg(
        project_meter_energy_mwh.where(is_sunny), agg=Aggregation.SUM
    )


def solv_period_kwh_lost(
    *,
    project_irradiance_poa_w_m2_5m: xr.DataArray,
    unit_power_ac_kw_5m: xr.DataArray,
    unit_power_setpoint_kw_5m: xr.DataArray,
    project_meter_power_kw_5m: xr.DataArray,
    unit_ac_capacity_kw: xr.DataArray,
    unit_dc_capacity_kw: xr.DataArray,
    project_expected_energy_kwh_5m: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    ##
    # Define constants
    #

    CLIPPING_THRESHOLD = 0.99
    NORMALIZED_THRESHOLD_FOR_NO_POWER = 0.001
    DERATED_THRESHOLD = 0.90
    WINDOW_SIZE_FOR_DERATED_THRESHOLD = 12

    is_sunny = solv_is_sunny(
        project_irradiance_poa_w_m2_5m=project_irradiance_poa_w_m2_5m
    )

    ##
    # Calculate the Period MWh Lost
    # This is a multi-step process
    #

    # Step 1: For Off-line Units

    # reduces unit power such that the total unit power is equal to the project meter power
    revised_unit_kw = (
        unit_power_ac_kw_5m
        / unit_power_ac_kw_5m.sum(dim=DeviceType.PV_PCS.name.lower())
        * project_meter_power_kw_5m
    )
    # original contract also specifies that the unit is clipping when current is greater than the current
    # setpoint, but we did not have access to current setpoint data.
    unit_is_clipping_5m = (
        unit_power_ac_kw_5m > unit_power_setpoint_kw_5m * CLIPPING_THRESHOLD
    )
    unit_ac_or_dc_capacity_kw_5m = xr.where(
        unit_is_clipping_5m, unit_ac_capacity_kw, unit_dc_capacity_kw
    )
    project_average_of_all_units_ac_or_dc_capacity_kw_5m = (
        unit_ac_or_dc_capacity_kw_5m.mean(dim=DeviceType.PV_PCS.name.lower())
    )
    normalized_unit_kw = (
        revised_unit_kw
        * project_average_of_all_units_ac_or_dc_capacity_kw_5m
        / unit_ac_or_dc_capacity_kw_5m
    )
    norm_p80 = normalized_unit_kw.quantile(
        dim=DeviceType.PV_PCS.name.lower(), q=0.8
    ).drop("quantile")
    average_unit_nv = normalized_unit_kw.where(normalized_unit_kw > norm_p80).mean(
        dim=DeviceType.PV_PCS.name.lower()
    )
    unit_power_lost_when_offline_kw_5m = (
        average_unit_nv
        * unit_ac_or_dc_capacity_kw_5m
        / project_average_of_all_units_ac_or_dc_capacity_kw_5m
    )

    unit_energy_lost_when_offline_kwh_5m = unit_power_lost_when_offline_kw_5m / 12

    unit_is_offline = (
        unit_power_ac_kw_5m < NORMALIZED_THRESHOLD_FOR_NO_POWER * unit_ac_capacity_kw
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
        {Time.TIME_5MIN_UTC.value: WINDOW_SIZE_FOR_DERATED_THRESHOLD}
    ).min()
    unit_is_derated_5m = (
        previous_hour_meets_threshold.rolling(
            {Time.TIME_5MIN_UTC.value: WINDOW_SIZE_FOR_DERATED_THRESHOLD}
        )
        .max()
        .shift({Time.TIME_5MIN_UTC.value: -(WINDOW_SIZE_FOR_DERATED_THRESHOLD - 1)})
    )
    unit_is_derated_5m = unit_is_derated_5m.astype(bool)

    # Step 3: For Facility Offline

    facility_is_offline = unit_is_offline.all(dim=DeviceType.PV_PCS.name.lower())

    ## The contract has very specific language about the expected energy model used
    # however, since we do not have access to the month-of-year initial expected energy model, we
    # instead use our internal expected energy model.

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
        dim=DeviceType.PV_PCS.name.lower()
    )

    # at the facility level

    project_energy_lost_kwh_5m = xr.where(
        ~is_sunny | is_excuse_event,
        0,
        xr.where(
            facility_is_offline,
            project_expected_energy_kwh_5m,
            project_energy_lost_kwh_5m,
        ),
    )

    # The sum result

    period_kwh_lost = time_combiner.agg(project_energy_lost_kwh_5m, agg=Aggregation.SUM)

    return period_kwh_lost


def solv_guarantee_availability(
    *,
    period_kwh_produced: xr.DataArray,
    period_kwh_lost: xr.DataArray,
) -> xr.DataArray:
    return period_kwh_produced / (period_kwh_produced + period_kwh_lost)
