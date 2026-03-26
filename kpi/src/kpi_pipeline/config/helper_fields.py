from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.services import process
from kpi_pipeline.services.calc import CalcProcess, ProcessCalc, SelectCalc
from kpi_pipeline.services.process import (
    AggFirstProcess,
    AggregateProcess,
    ProcessList,
)


def _aggregate(
    var: str,
    agg: Aggregation,
    high_res_time_axis: Time = Time.TIME_5MIN_UTC,
    low_res_time_axis: Time = Time.DATE_LOCAL,
    child_device_axis: DeviceType | None = None,
    parent_device_axis: DeviceType | None = None,
) -> Field:
    combiner_model = CoordCombinerModel(
        high_res_time_axis=high_res_time_axis,
        low_res_time_axis=low_res_time_axis,
        child_device_axis=child_device_axis,
        parent_device_axis=parent_device_axis,
    )
    return Field(
        ProcessCalc(
            var=var,
            process=AggregateProcess(agg=agg, combiner_model=combiner_model),
        )
    )


def _device_aggregate(
    var: str,
    agg: Aggregation,
    child_device_axis: DeviceType,
    parent_device_axis: DeviceType | None = None,
):
    combiner_model = CoordCombinerModel(
        child_device_axis=child_device_axis,
        parent_device_axis=parent_device_axis,
    )
    return Field(
        ProcessCalc(
            var=var,
            process=AggregateProcess(agg=agg, combiner_model=combiner_model),
        )
    )


def _resample_groupby(
    field: str,
    agg_resample: Aggregation,
    agg_groupby: Aggregation,
    from_device_axis: DeviceType,
):
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=ProcessList(
                steps=[
                    AggregateProcess(
                        agg=agg_resample,
                        combiner_model=_5min_to_daily(),
                    ),
                    AggregateProcess(
                        agg=agg_groupby,
                        combiner_model=CoordCombinerModel(
                            child_device_axis=from_device_axis,
                        ),
                    ),
                ]
            ),
        )
    )


def _5min_to_daily(
    child_device_axis: DeviceType | None = None,
    parent_device_axis: DeviceType | None = None,
) -> CoordCombinerModel:
    return CoordCombinerModel(
        high_res_time_axis=Time.TIME_5MIN_UTC,
        low_res_time_axis=Time.DATE_LOCAL,
        child_device_axis=child_device_axis,
        parent_device_axis=parent_device_axis,
    )


def _agg_first(
    var: str,
) -> Field:
    return Field(
        ProcessCalc(
            var=var,
            process=AggFirstProcess(time_combiner_model=_5min_to_daily()),
        )
    )


def _fill_energy_accumulator(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.ProcessList(
                steps=[process.ForwardFillProcess(), process.BackwardFillProcess()],
            ),
        )
    )
