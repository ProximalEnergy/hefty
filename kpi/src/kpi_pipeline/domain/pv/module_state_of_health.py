from typing import Optional

import xarray as xr
from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.protocols import CoordCombinerProtocol
from kpi_pipeline.domain.general import diff


def pv_dc_combiner_module_excess_degradation(
    *,
    met_station_irradiance_poa_w_m2_5m: xr.DataArray,
    project_theoretical_poa_irradiance_w_m2_5m: xr.DataArray,
    project_meter_power_kw_5m: xr.DataArray,
    project_poi_limit_kw: xr.DataArray,
    pv_pcs_ac_power_kw_5m: xr.DataArray,
    pv_pcs_ac_power_capacity_kw: xr.DataArray,
    pv_pcs_reactive_power_kvar_5m: xr.DataArray,
    pv_pcs_module_voltage_v_5m: xr.DataArray,
    pv_pcs_module_power_kw_5m: xr.DataArray,
    pv_pcs_module_power_capacity_kw: xr.DataArray,
    block_tracker_deviation_from_setpoint_deg_d: xr.DataArray,
    block_tracker_setpoint_deviation_from_median_deg_d: xr.DataArray,
    pv_dc_combiner_field_health_d: xr.DataArray,
    pv_dc_combiner_current_amps_5m: xr.DataArray,
    pv_dc_combiner_expected_energy_kwh_5m: xr.DataArray,
    daily_combiner: CoordCombinerProtocol,
    broadcast_pcs_to_combiner: CoordCombinerProtocol,
    broadcast_block_to_combiner: CoordCombinerProtocol,
    module_to_pcs_combiner: CoordCombinerProtocol,
    final_time_combiner: CoordCombinerProtocol,
    pv_pcs_ac_power_setpoint_kw_5m: Optional[xr.DataArray] = None,
    # todo: for north star use pv pcs voltage
    pv_pcs_voltage_v_5m: Optional[xr.DataArray] = None,
    min_poa: float = 250.0,
    max_poa_1d: float = 20.0,
    max_poa_std: float = 7.5,
    max_poa_std_1d: float = 2.5,
) -> xr.DataArray:
    """
    Result is daily kpi for id 17 which is at the pv dc combiner level.
    """

    ##
    # Define helper functions
    #

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
        trkr_scores = daily_combiner.agg(exceeds_theoretical, agg=Aggregation.SUM)

        # Remove bad trackers (scores < mean * 0.9)
        mean_score = trkr_scores.mean(dim=DeviceType.MET_STATION.name.lower())
        good_trackers = trkr_scores >= (mean_score * 0.9)
        return met_station_poa.where(daily_combiner.broadcast(good_trackers))

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
        diff_forward = abs(diff(met_station_clean_poa_5m, time_dim=Time.TIME_5MIN_UTC))
        # Backward diff: shift forward by 1 and subtract
        diff_backward = abs(
            met_station_clean_poa_5m
            - met_station_clean_poa_5m.shift({Time.TIME_5MIN_UTC.value: 1})
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
                {Time.TIME_5MIN_UTC.value: 3}, center=True
            ).mean()  # rolling 15 minute average
        )

        good_std = std_rolling_15_minute_average <= max_poa_std

        # Calculate change in std from time step to time step
        std_diff_forward = abs(
            diff(std_rolling_15_minute_average, time_dim=Time.TIME_5MIN_UTC)
        )
        # Backward diff: shift forward by 1 and subtract
        std_diff_backward = abs(
            std_rolling_15_minute_average
            - std_rolling_15_minute_average.shift({Time.TIME_5MIN_UTC.value: 1})
        )
        std_1d = std_diff_forward + std_diff_backward

        std_1d_good = std_1d <= max_poa_std_1d

        # Good if: (std good OR std_1d good) AND irr good AND der good
        good_idx: xr.DataArray = (good_std | std_1d_good) & good_irr & good_der

        # Filter to keep only good indices
        return good_idx

    def _project_good_indices_1d(
        project_good_poa_indices_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Make sure that there are at least 12 5 minute intervals, otherwise set all indices to False for that particular day
        """
        at_least_12_good_itervals = (
            daily_combiner.agg(project_good_poa_indices_5m, agg=Aggregation.SUM) >= 12
        )

        return at_least_12_good_itervals

    def _combiner_good_indices_d() -> xr.DataArray:
        """
        If DC Field health is less than 0.975 of the mean dc field health across all combiners or 0.975 whichever is smaller,
        do not calculate soh for that day for that combiner
        """
        # Calculate the mean DC field health across all combiners for each day
        mean_dc_field_health = pv_dc_combiner_field_health_d.mean(
            dim=DeviceType.PV_DC_COMBINER.name.lower()
        )
        # Clip the mean to a maximum of 0.975 (ensures threshold doesn't exceed 0.975)
        effective_mean_dc_field_health = (mean_dc_field_health * 0.975).clip(max=0.975)
        # Mark combiners as having good fuse health if their health is greater than the effective mean
        # (combiners with health above the threshold are considered good for SOH calculation)
        good_fuse_health = (
            pv_dc_combiner_field_health_d > effective_mean_dc_field_health
        )

        return good_fuse_health

    def _pcs_good_indices_inverter_itself_5m() -> xr.DataArray:
        """
        Only use intervals where inverter power is between 5% and 95% of it's capacity
        Also only use intervals where the inverter setpoint is greater than 98% of the inverter capacity
        Only use intervals where the power factor is greater than 0.98
        """
        power_good_idx = (
            pv_pcs_ac_power_kw_5m <= (0.95 * pv_pcs_ac_power_capacity_kw)
        ) & (pv_pcs_ac_power_kw_5m >= (0.05 * pv_pcs_ac_power_capacity_kw))
        setpoint_good_idx = xr.DataArray(True)
        if pv_pcs_ac_power_setpoint_kw_5m is not None:
            pv_pcs_ac_power_setpoint_filled = pv_pcs_ac_power_setpoint_kw_5m.fillna(
                pv_pcs_ac_power_capacity_kw
            )
            setpoint_good_idx = pv_pcs_ac_power_setpoint_filled >= (
                0.98 * pv_pcs_ac_power_capacity_kw
            )
        apparent_power = (
            pv_pcs_ac_power_kw_5m**2 + pv_pcs_reactive_power_kvar_5m**2
        ) ** 0.5
        power_factor = xr.where(
            apparent_power > 0, pv_pcs_ac_power_kw_5m / apparent_power, 0.0
        )
        power_factor_good_idx = power_factor >= 0.98
        return power_good_idx & setpoint_good_idx & power_factor_good_idx  # type: ignore

    def _pcs_from_child_module_good_indices_5m() -> xr.DataArray:
        """
        Pcs modules' voltages must have a range less than 5 V
        Make sure both/all child pcs modules are greater than 5% of operating capacity (ie ac power)
        """
        voltage_good_idx = (
            module_to_pcs_combiner.agg(pv_pcs_module_voltage_v_5m, agg=Aggregation.MAX)
            - module_to_pcs_combiner.agg(
                pv_pcs_module_voltage_v_5m, agg=Aggregation.MIN
            )
        ) < 5

        power_good_idx = module_to_pcs_combiner.group(
            pv_pcs_module_power_kw_5m > (0.05 * pv_pcs_module_power_capacity_kw)
        ).all(dim=module_to_pcs_combiner.dim())

        return voltage_good_idx & power_good_idx

    def _pv_dc_combiner_filtered_current_amp_5m() -> xr.DataArray:
        # 5 minute level

        clean_poa_5m = _met_station_clean_poa_5m()

        project_good_poa_indices_5m = _project_good_poa_indices_5m(clean_poa_5m)

        # meter power is not more than 99% of the poi limit (for solar + bess, you'll have to use some of circuit power)
        # todo handle case with solar + bess
        project_good_meter_indices_5m = project_meter_power_kw_5m <= (
            0.99 * project_poi_limit_kw
        )

        # Daily level good indices
        # project level
        # Make sure that there are at least 12 5 minute intervals, otherwise set all indices to False for that particular day
        project_good_indices_1d = (
            daily_combiner.agg(project_good_poa_indices_5m, agg=Aggregation.SUM) >= 12
        )

        # block level
        # If the block setpoint deviation or position deviation kpi is greater than 1 degree,
        # do not calculate soh for that day for that block
        block_good_indices_d = (block_tracker_deviation_from_setpoint_deg_d < 1) & (
            block_tracker_setpoint_deviation_from_median_deg_d < 1
        )

        # combiner level

        combiner_good_indices_d = _combiner_good_indices_d()

        # daily across all levels

        combiner_good_indices_all_d = (
            combiner_good_indices_d
            & broadcast_block_to_combiner.broadcast(block_good_indices_d)
            & project_good_indices_1d
        )

        combiner_good_indices_5m = (
            daily_combiner.broadcast(combiner_good_indices_all_d)
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

        pv_pcs_voltage_v_5m = module_to_pcs_combiner.agg(
            pv_pcs_module_voltage_v_5m, agg=Aggregation.MEAN
        )

        return pv_pcs_voltage_v_5m.where(pcs_good_indices_5m)

    def _combiner_pre_filtered_module_degradation(
        combiner_current_amps_5m: xr.DataArray,
        pv_pcs_voltage_v_5m: xr.DataArray,
    ) -> xr.DataArray:
        # / 1000 converts watts to kilowatts
        combiner_actual_power_5m = (
            combiner_current_amps_5m
            * broadcast_pcs_to_combiner.broadcast(pv_pcs_voltage_v_5m)
        ) / 1000
        # converting 5 minute power to kwh by dividing by 12 (5 minutes * 12 = 1 hour)
        combiner_actual_energy_kwh_5m = combiner_actual_power_5m / 12

        # only use concurrent time stamps (where both are not null)
        valid_mask = (
            pv_dc_combiner_expected_energy_kwh_5m.notnull()
            & combiner_actual_energy_kwh_5m.notnull()
        )

        total_expected_energy_kwh_d = final_time_combiner.agg(
            pv_dc_combiner_expected_energy_kwh_5m.where(valid_mask), agg=Aggregation.SUM
        )
        total_actual_energy_kwh_d = final_time_combiner.agg(
            combiner_actual_energy_kwh_5m.where(valid_mask), agg=Aggregation.SUM
        )
        return (total_actual_energy_kwh_d / total_expected_energy_kwh_d).where(
            total_expected_energy_kwh_d != 0
        )

    ##
    # Perform Logic
    #

    pv_dc_combiner_filtered_current_amps_5m = _pv_dc_combiner_filtered_current_amp_5m()

    pv_pcs_filtered_voltage_v_5m = _pcs_filtered_voltage_v_5m()

    module_degradation = _combiner_pre_filtered_module_degradation(
        combiner_current_amps_5m=pv_dc_combiner_filtered_current_amps_5m,
        pv_pcs_voltage_v_5m=pv_pcs_filtered_voltage_v_5m,
    )

    # if less than 15% of devices reporting, then skip that particular day
    valid_percentage = module_degradation.notnull().mean(
        dim=DeviceType.PV_DC_COMBINER.name.lower()
    )

    validity_mask = valid_percentage >= 0.15

    return module_degradation.where(validity_mask)
