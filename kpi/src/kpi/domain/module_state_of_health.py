import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.base.util import coord
from kpi.domain.util import date_local, diff


def pv_dc_combiner_module_excess_degradation(
    *,
    met_station_irradiance_poa_w_m2_5m: xr.DataArray,
    project_theoretical_poa_irradiance_w_m2_5m: xr.DataArray,
    project_meter_power_kw_5m: xr.DataArray,
    project_poi_limit_kw: xr.DataArray,
    pv_inverter_ac_power_kw_5m: xr.DataArray,
    pv_inverter_ac_power_capacity_kw: xr.DataArray,
    pv_inverter_reactive_power_kvar_5m: xr.DataArray,
    pv_inverter_module_voltage_v_5m: xr.DataArray,
    pv_inverter_module_power_kw_5m: xr.DataArray,
    pv_inverter_module_power_capacity_kw: xr.DataArray,
    block_tracker_deviation_from_setpoint_deg_d: xr.DataArray,
    block_tracker_setpoint_deviation_from_median_deg_d: xr.DataArray,
    pv_dc_combiner_field_health_d: xr.DataArray,
    pv_dc_combiner_current_amps_5m: xr.DataArray,
    pv_dc_combiner_expected_energy_kwh_5m: xr.DataArray,
    date_local_5m: xr.DataArray,
    combiner_to_inverter: xr.DataArray,
    combiner_to_block: xr.DataArray,
    inverter_module_to_inverter: xr.DataArray,
    pv_inverter_ac_power_setpoint_kw_5m: xr.DataArray | None = None,
    # todo: for north star use pv inverter voltage
    pv_inverter_voltage_v_5m: xr.DataArray | None = None,
    min_poa: float = 250.0,
    max_poa_1d: float = 20.0,
    max_poa_std: float = 7.5,
    max_poa_std_1d: float = 2.5,
) -> xr.DataArray:
    """
    Result is daily kpi for id 17 which is at the pv dc combiner level.
    """

    _ = pv_inverter_voltage_v_5m

    ##
    # Define helper functions
    #

    date = date_local(date_local_5m)

    def _met_station_clean_poa_5m() -> xr.DataArray:
        # Filter values > min_poa
        met_station_poa = met_station_irradiance_poa_w_m2_5m.where(
            met_station_irradiance_poa_w_m2_5m > 10.0
        )

        # Calculate tracker scores: count non-null values where measured > theoretical
        # Select values where measured > theoretical
        exceeds_theoretical = (
            met_station_poa > project_theoretical_poa_irradiance_w_m2_5m
        )
        trkr_scores = exceeds_theoretical.groupby(date).sum()

        # Remove bad trackers (scores < mean * 0.9)
        mean_score = trkr_scores.mean(dim=DeviceType.MET_STATION.name.lower())
        good_trackers = trkr_scores >= (mean_score * 0.9)
        return met_station_poa.where(
            good_trackers.sel({TimeCoords.DATE_LOCAL.value: date_local_5m}).drop_vars(
                TimeCoords.DATE_LOCAL.value
            )
        )

    def _project_good_poa_indices_5m(
        met_station_clean_poa_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Filter irradiance data by removing bad trackers and invalid time periods.
        """

        # generic clear sky check
        median_poa = met_station_clean_poa_5m.median(
            dim=DeviceType.MET_STATION.name.lower()
        )
        good_irr = median_poa >= min_poa

        # Calculate 1d change (absolute difference between consecutive time steps)
        diff_forward = abs(
            diff(met_station_clean_poa_5m, time_dim=TimeCoords.TIME_5MIN_UTC)
        )
        # Backward diff: shift forward by 1 and subtract
        diff_backward = abs(
            met_station_clean_poa_5m
            - met_station_clean_poa_5m.shift({TimeCoords.TIME_5MIN_UTC.value: 1})
        )
        met_station_poa_1d = diff_forward + diff_backward

        # Good if mean 1d change <= max_poa_1d
        good_der = (
            met_station_poa_1d.mean(dim=DeviceType.MET_STATION.name.lower())
            <= max_poa_1d
        )

        # Calculate rolling standard deviation across devices
        project_std_across_devices = met_station_clean_poa_5m.std(
            dim=DeviceType.MET_STATION.name.lower()
        )
        std_rolling_15_minute_average = (
            project_std_across_devices.rolling(
                {TimeCoords.TIME_5MIN_UTC.value: 3}, center=True
            ).mean()  # rolling 15 minute average
        )

        good_std = std_rolling_15_minute_average <= max_poa_std

        # Calculate change in std from time step to time step
        std_diff_forward = abs(
            diff(std_rolling_15_minute_average, time_dim=TimeCoords.TIME_5MIN_UTC)
        )
        # Backward diff: shift forward by 1 and subtract
        std_diff_backward = abs(
            std_rolling_15_minute_average
            - std_rolling_15_minute_average.shift({TimeCoords.TIME_5MIN_UTC.value: 1})
        )
        std_1d = std_diff_forward + std_diff_backward

        std_1d_good = std_1d <= max_poa_std_1d

        # Good if: (std good OR std_1d good) AND irr good AND der good
        good_idx: xr.DataArray = (good_std | std_1d_good) & good_irr & good_der

        # Filter to keep only good indices
        return good_idx

    def _combiner_good_indices_d() -> xr.DataArray:
        """
        If DC field health is below 0.975 times the mean across combiners (capped
        at 0.975), skip SOH for that combiner that day.
        """
        # Calculate the mean DC field health across all combiners for each day
        mean_dc_field_health = pv_dc_combiner_field_health_d.mean(
            dim=DeviceType.PV_DC_COMBINER.name.lower()
        )
        # Cap scaled mean at 0.975 so the threshold never exceeds 0.975.
        effective_mean_dc_field_health = (mean_dc_field_health * 0.975).clip(max=0.975)
        # Good fuse health: combiner health above effective mean (eligible for SOH)
        good_fuse_health = (
            pv_dc_combiner_field_health_d > effective_mean_dc_field_health
        )

        return good_fuse_health

    def _pcs_good_indices_inverter_itself_5m() -> xr.DataArray:
        """
        Keep intervals where inverter power is 5–95% of capacity, setpoint (if
        present) is at least 98% of capacity, and power factor is at least 0.98.
        """
        power_good_idx = (
            pv_inverter_ac_power_kw_5m <= (0.95 * pv_inverter_ac_power_capacity_kw)
        ) & (pv_inverter_ac_power_kw_5m >= (0.05 * pv_inverter_ac_power_capacity_kw))
        setpoint_good_idx = xr.DataArray(True)
        if pv_inverter_ac_power_setpoint_kw_5m is not None:
            pv_inverter_ac_power_setpoint_filled = (
                pv_inverter_ac_power_setpoint_kw_5m.fillna(
                    pv_inverter_ac_power_capacity_kw
                )
            )
            setpoint_good_idx = pv_inverter_ac_power_setpoint_filled >= (
                0.98 * pv_inverter_ac_power_capacity_kw
            )
        apparent_power = (
            pv_inverter_ac_power_kw_5m**2 + pv_inverter_reactive_power_kvar_5m**2
        ) ** 0.5
        power_factor = xr.where(
            apparent_power > 0, pv_inverter_ac_power_kw_5m / apparent_power, 0.0
        )
        power_factor_good_idx = power_factor >= 0.98
        return power_good_idx & setpoint_good_idx & power_factor_good_idx

    inverter = inverter_module_to_inverter.rename(coord(DeviceType.PV_INVERTER))

    def _pcs_from_child_module_good_indices_5m() -> xr.DataArray:
        """
        PCS module voltages must span less than 5 V; each child module AC power
        must exceed 5% of operating capacity.
        """
        voltage_good_idx = (
            pv_inverter_module_voltage_v_5m.groupby(inverter).max()
            - pv_inverter_module_voltage_v_5m.groupby(inverter).min()
            < 5
        )

        power_good_idx = (
            (
                pv_inverter_module_power_kw_5m
                > (0.05 * pv_inverter_module_power_capacity_kw)
            )
            .groupby(inverter)
            .all()
        )

        return voltage_good_idx & power_good_idx

    def _pv_dc_combiner_filtered_current_amp_5m() -> xr.DataArray:
        # 5 minute level

        clean_poa_5m = _met_station_clean_poa_5m()

        project_good_poa_indices_5m = _project_good_poa_indices_5m(clean_poa_5m)

        # Meter power at most 99% of POI limit (solar+BESS may need circuit power).
        # todo: handle solar + BESS
        project_good_meter_indices_5m = project_meter_power_kw_5m <= (
            0.99 * project_poi_limit_kw
        )

        # Daily level good indices
        # project level
        # At least twelve good 5-minute intervals per day at project level.
        project_good_indices_1d = project_good_poa_indices_5m.groupby(date).sum() >= 12

        # Block level: skip SOH if tracker setpoint or position deviation >= 1°.
        block_good_indices_d = (block_tracker_deviation_from_setpoint_deg_d < 1) & (
            block_tracker_setpoint_deviation_from_median_deg_d < 1
        )

        # combiner level

        combiner_good_indices_d = _combiner_good_indices_d()

        # daily across all levels

        combiner_good_indices_all_d = (
            combiner_good_indices_d
            & block_good_indices_d.sel(
                {coord(DeviceType.BESS_BLOCK): combiner_to_block}
            ).drop_vars(coord(DeviceType.BESS_BLOCK))
            & project_good_indices_1d
        )

        combiner_good_indices_5m = (
            (
                combiner_good_indices_all_d.sel(
                    {TimeCoords.DATE_LOCAL.value: date_local_5m}
                ).drop_vars(TimeCoords.DATE_LOCAL.value)
            )
            & project_good_poa_indices_5m
            & project_good_meter_indices_5m
        )

        return pv_dc_combiner_current_amps_5m.where(combiner_good_indices_5m)

    def _pcs_filtered_voltage_v_5m() -> xr.DataArray:
        pcs_good_indices_inverter_itself_5m = _pcs_good_indices_inverter_itself_5m()

        pcs_from_child_module_good_indices_5m = _pcs_from_child_module_good_indices_5m()

        pcs_good_indices_5m = (
            pcs_good_indices_inverter_itself_5m & pcs_from_child_module_good_indices_5m
        )

        pv_inverter_voltage_v_5m = pv_inverter_module_voltage_v_5m.groupby(
            inverter
        ).mean()

        return pv_inverter_voltage_v_5m.where(pcs_good_indices_5m)

    def _combiner_pre_filtered_module_degradation(
        combiner_current_amps_5m: xr.DataArray,
        pv_inverter_voltage_v_5m: xr.DataArray,
    ) -> xr.DataArray:
        # / 1000 converts watts to kilowatts
        combiner_actual_power_5m = (
            combiner_current_amps_5m
            * pv_inverter_voltage_v_5m.sel(
                {coord(DeviceType.PV_INVERTER): combiner_to_inverter}
            ).drop_vars(coord(DeviceType.PV_INVERTER))
        ) / 1000

        # converting 5 minute power to kwh by dividing by 12 (5 minutes * 12 = 1 hour)
        combiner_actual_energy_kwh_5m = combiner_actual_power_5m / 12

        # only use concurrent time stamps (where both are not null)
        valid_mask = (
            pv_dc_combiner_expected_energy_kwh_5m.notnull()
            & combiner_actual_energy_kwh_5m.notnull()
        )

        total_expected_energy_kwh_d = (
            pv_dc_combiner_expected_energy_kwh_5m.where(valid_mask).groupby(date).sum()
        )
        total_actual_energy_kwh_d = (
            combiner_actual_energy_kwh_5m.where(valid_mask).groupby(date).sum()
        )
        return (total_actual_energy_kwh_d / total_expected_energy_kwh_d).where(
            total_expected_energy_kwh_d != 0
        )

    ##
    # Perform Logic
    #

    pv_dc_combiner_filtered_current_amps_5m = _pv_dc_combiner_filtered_current_amp_5m()

    pv_inverter_filtered_voltage_v_5m = _pcs_filtered_voltage_v_5m()

    module_degradation = _combiner_pre_filtered_module_degradation(
        combiner_current_amps_5m=pv_dc_combiner_filtered_current_amps_5m,
        pv_inverter_voltage_v_5m=pv_inverter_filtered_voltage_v_5m,
    )

    # if less than 15% of devices reporting, then skip that particular day
    valid_percentage = module_degradation.notnull().mean(
        dim=DeviceType.PV_DC_COMBINER.name.lower()
    )

    validity_mask = valid_percentage >= 0.15

    return module_degradation.where(validity_mask)
