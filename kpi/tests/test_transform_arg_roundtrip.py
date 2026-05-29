"""JSON round-trip guards for transform arg types."""

from unittest.mock import patch

import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import TimeCoord
from kpi.base.exception import NoDownloadedDataError
from kpi.domain.agg.across_devices import sum_across_devices
from kpi.domain.general import filter_by_value
from kpi.domain.util import diff
from kpi.op.observer import LocalObserver, use_observer
from kpi.op.pipeline_schema import PipelineSchema
from kpi.op.plan import MultiFieldPlan, PipelinePlan
from kpi.op.transform.arg import (
    Constant,
    DeviceTypeConstant,
    Required,
    TimeCoordConstant,
)
from kpi.op.transform.method import MethodCalc
from kpi.op.transform.schema import CalcSchema


def _round_trip(method: MethodCalc) -> MethodCalc:
    """Serialize and validate a transform method through JSON."""
    return MethodCalc.model_validate_json(method.model_dump_json())


def test_json_round_trip_rehydrates_device_type_arg() -> None:
    """DeviceTypeConstant values return as enum instances."""
    method = MethodCalc(
        fn=sum_across_devices,
        args=(Required(field_name="x"),),
        keyword_args={
            "device_type": DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS)
        },
    )

    result = _round_trip(method).keyword_args["device_type"]

    assert isinstance(result, DeviceTypeConstant)
    assert result.value is DeviceTypeEnum.BESS_PCS


def test_json_round_trip_rehydrates_time_coord_arg() -> None:
    """TimeCoordConstant values return as enum instances."""
    method = MethodCalc(
        fn=diff,
        args=(Required(field_name="x"),),
        keyword_args={"time_dim": TimeCoordConstant(value=TimeCoord.DATE_LOCAL)},
    )

    result = _round_trip(method).keyword_args["time_dim"]

    assert isinstance(result, TimeCoordConstant)
    assert result.value is TimeCoord.DATE_LOCAL


def test_json_round_trip_preserves_numeric_constant() -> None:
    """Plain numeric constants still use Constant."""
    method = MethodCalc(
        fn=filter_by_value,
        args=(Required(field_name="x"),),
        keyword_args={"min_value": Constant(value=0)},
    )

    result = _round_trip(method).keyword_args["min_value"]

    assert isinstance(result, Constant)
    assert result.value == 0
    assert type(result.value) is int


def test_pipeline_schema_json_round_trip_rehydrates_enum_arg() -> None:
    """Nested transform methods also rehydrate explicit enum args."""
    method = MethodCalc(
        fn=sum_across_devices,
        args=(Required(field_name="x"),),
        keyword_args={
            "device_type": DeviceTypeConstant(value=DeviceTypeEnum.BESS_STRING)
        },
    )
    pipeline = PipelineSchema(map={"transform": CalcSchema(map={"field": method})})

    result = PipelineSchema.model_validate_json(pipeline.model_dump_json())
    transform = result.map["transform"]

    assert isinstance(transform, CalcSchema)
    arg = transform.map["field"].keyword_args["device_type"]
    assert isinstance(arg, DeviceTypeConstant)
    assert arg.value is DeviceTypeEnum.BESS_STRING


def _raise_no_downloaded_data(
    self: CalcSchema, *, dataset: xr.Dataset, plan: MultiFieldPlan
) -> xr.Dataset:
    del self, dataset, plan
    raise NoDownloadedDataError("missing")


def test_run_preserves_dataset_when_observer_swallows_error() -> None:
    """A skipped schema-level error does not replace the dataset with None."""
    dataset = xr.Dataset()
    schema = PipelineSchema(map={"transform": CalcSchema(map={})})
    plan = PipelinePlan(steps={"transform": MultiFieldPlan(fields=[])})
    with use_observer(LocalObserver()):
        with patch.object(CalcSchema, "run", _raise_no_downloaded_data):
            result = schema.run(dataset=dataset, plan=plan)

    assert result is dataset
