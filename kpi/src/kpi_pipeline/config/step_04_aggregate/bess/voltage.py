from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.config.helper_fields import _aggregate
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESSVoltage(AddCalculationsSchema):
    # ============================================================================
    # Voltage Aggregations
    # ============================================================================
    # Aggregates cell voltage from 5-minute to daily, including averages,
    # minimums, and maximums

    bess_string_avg_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_avg_cell_voltage_v_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_string_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_avg_cell_voltage_v_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_min_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_min_cell_voltage_v_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_min_cell_voltage_v_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_max_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_max_cell_voltage_v_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_max_cell_voltage_v_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )
