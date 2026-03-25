from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.helper_fields import (
    _aggregate,
    _device_aggregate,
    _resample_groupby,
)
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESSState(AddCalculationsSchema):
    # ============================================================================
    # Degradation and Depth of Discharge (DOD)
    # ============================================================================
    # Calculates string degradation and depth of discharge metrics

    project_total_string_degradation_d = _resample_groupby(
        field=Calculate.bess_string_degradation_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_total_degradation_d = _aggregate(
        var=Calculate.bess_string_degradation_5m.var,
        agg=Aggregation.SUM,
    )

    bess_bank_avg_dod_d = _aggregate(
        var=Calculate.bess_bank_dod_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_dod_d = _aggregate(
        var=Calculate.bess_bank_dod_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )

    project_avg_dod_d = _aggregate(
        var=Calculate.project_dod_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_string_dod_d = _aggregate(
        var=Calculate.bess_string_dod_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_dod_d = _aggregate(
        var=Calculate.bess_string_dod_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # State of Charge (SOC) Aggregations
    # ============================================================================
    # Aggregates state of charge from 5-minute to daily at various device levels

    bess_bank_avg_soc_d = _aggregate(
        var=Validate.bess_bank_soc_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_soc_d = _aggregate(
        var=Validate.bess_bank_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )
    bess_block_avg_soc_d = _aggregate(
        var=Validate.bess_block_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_block_soc_d = _aggregate(
        var=Validate.bess_block_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BLOCK,
    )

    project_avg_soc_d = _aggregate(
        var=Validate.project_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    project_string_soc_variance_d = _aggregate(
        var=Calculate.bess_project_string_soc_variance_5m.var,
        agg=Aggregation.MEAN,
    )

    bess_pcs_string_soc_variance_d = _aggregate(
        var=Calculate.bess_pcs_string_soc_variance_5m.var,
        agg=Aggregation.MEAN,
    )

    project_pcs_string_soc_variance_d = _aggregate(
        var=Calculate.bess_pcs_string_soc_variance_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )

    project_string_soc_balance_score_d = Field(
        calc.SocBalanceScoreCalc(
            soc_variance_var=project_string_soc_variance_d.var,
        )
    )

    bess_pcs_string_soc_balance_score_d = Field(
        calc.SocBalanceScoreCalc(
            soc_variance_var=bess_pcs_string_soc_variance_d.var,
        )
    )

    project_pcs_string_soc_balance_score_d = Field(
        calc.SocBalanceScoreCalc(
            soc_variance_var=project_pcs_string_soc_variance_d.var,
        )
    )

    ##
    # string SOC
    #

    # average
    project_avg_string_soc_d = _aggregate(
        var=Validate.bess_string_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_soc_d = _aggregate(
        var=Validate.bess_string_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # Resting State of Charge (SOC) Aggregations
    # ============================================================================
    # Aggregates resting SOC (SOC when system is not actively charging/discharging)
    # from 5-minute to daily at various device levels

    bess_bank_avg_resting_soc_d = _aggregate(
        var=Calculate.bess_bank_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_resting_soc_d = _aggregate(
        var=Calculate.bess_bank_resting_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )

    bess_block_avg_resting_soc_d = _aggregate(
        var=Calculate.bess_block_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_block_resting_soc_d = _aggregate(
        var=Calculate.bess_block_resting_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BLOCK,
    )

    project_avg_resting_soc_d = _aggregate(
        var=Calculate.project_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    ##
    # string resting SOC
    #

    # average

    project_avg_string_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    # max

    bess_string_max_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )

    # min

    bess_string_min_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    # enclosure aggregations from string
    # enclosure values are derived from the string values

    bess_enclosure_avg_resting_soc_d = _device_aggregate(
        var=bess_string_avg_resting_soc_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
        parent_device_axis=DeviceType.BESS_ENCLOSURE,
    )

    bess_enclosure_max_resting_soc_d = _device_aggregate(
        var=bess_string_max_resting_soc_d.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
        parent_device_axis=DeviceType.BESS_ENCLOSURE,
    )

    bess_enclosure_min_resting_soc_d = _device_aggregate(
        var=bess_string_min_resting_soc_d.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
        parent_device_axis=DeviceType.BESS_ENCLOSURE,
    )

    # ============================================================================
    # State of Health (SOH) Aggregations
    # ============================================================================
    # Aggregates state of health from 5-minute to daily at bank and string levels

    bess_bank_avg_soh_d = _aggregate(
        var=Validate.bess_bank_soh_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_soh_d = _aggregate(
        var=Validate.bess_bank_soh_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )
    project_avg_string_soh_d = _aggregate(
        var=Validate.bess_string_soh_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_soh_d = _aggregate(
        var=Validate.bess_string_soh_5m.var,
        agg=Aggregation.MEAN,
    )
