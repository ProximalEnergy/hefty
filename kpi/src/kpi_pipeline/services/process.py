from collections.abc import Callable
from typing import TypeVar

import xarray as xr
from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.models import ContextModel, CoordCombinerModel
from kpi_pipeline.base.protocols import ProcessProtocol
from kpi_pipeline.domain.bess import (
    event_change_to_in_event,
    is_charging,
    is_discharging,
    is_idling,
    resting_soc,
)
from kpi_pipeline.domain.general import (
    accumulator_differences,
    agg_first,
    availability,
    clamp,
    diff,
    filter_to_range,
    from_rate_of_change_to_total,
    from_total_to_rate_of_change,
    is_between_values,
    remove_flat_lining,
    verify_within_range,
)
from kpi_pipeline.infra.calc_function_checker import verify_process_function_alignment
from kpi_pipeline.infra.coord_mapping import coord_combiner
from kpi_pipeline.infra.utils import (
    cast_type,
    fillna,
)
from pydantic import BaseModel

ProcessType = TypeVar("ProcessType", bound=ProcessProtocol)


def process(cls: type[ProcessType]) -> type[ProcessType]:
    if not issubclass(cls, ProcessProtocol):
        raise TypeError(f"{cls} is not a ProcessProtocol")
    return cls


def domain_process(
    domain_function: Callable,
) -> Callable[[type[ProcessType]], type[ProcessType]]:
    def decorator(cls: type[ProcessType]) -> type[ProcessType]:
        problems = verify_process_function_alignment(cls, domain_function)
        if problems:
            error_msg = "Process function alignment issues:\n" + "\n".join(
                f"  • {problem}" for problem in problems
            )
            raise ValueError(error_msg)
        return cls

    return decorator


@process
class ProcessIdentity:
    def __call__(
        self,
        *,
        x: xr.DataArray,
        context: ContextModel,
    ) -> xr.DataArray:
        return x


@process
class ProcessList:
    def __init__(self, steps: list[ProcessProtocol]):
        self.steps = steps

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        for func in self.steps:
            x = func(x=x, context=context)
        return x


@process
class FillNAProcess:
    def __init__(self, processes: list[ProcessProtocol] = []):
        self.processes = processes

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return fillna(*[func(x=x, context=context) for func in self.processes])


@domain_process(diff)
class DiffProcess(BaseModel):
    time_dim: Time = Time.TIME_5MIN_UTC

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return diff(x, time_dim=self.time_dim)


@domain_process(clamp)
class ClampProcess(BaseModel):
    min_value: float | None = None
    max_value: float | None = None

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return clamp(x=x, min_value=self.min_value, max_value=self.max_value)


@domain_process(verify_within_range)
class VerifyWithinRangeProcess(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    left_inclusive: bool = True
    right_inclusive: bool = True

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return verify_within_range(
            x=x,
            min_value=self.min_value,
            max_value=self.max_value,
            left_inclusive=self.left_inclusive,
            right_inclusive=self.right_inclusive,
        )


@domain_process(is_between_values)
class IsBetweenValuesProcess(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    left_inclusive: bool = True
    right_inclusive: bool = True

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return is_between_values(
            x=x,
            min_value=self.min_value,
            max_value=self.max_value,
            left_inclusive=self.left_inclusive,
            right_inclusive=self.right_inclusive,
        )


@domain_process(filter_to_range)
class FilterToRangeProcess(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    left_inclusive: bool = True
    right_inclusive: bool = True

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return filter_to_range(
            x=x,
            min_value=self.min_value,
            max_value=self.max_value,
            left_inclusive=self.left_inclusive,
            right_inclusive=self.right_inclusive,
        )


@domain_process(cast_type)
class CastTypeProcess(BaseModel):
    dtype: str

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return cast_type(x=x, dtype=self.dtype)


@process
class NotNullProcess(BaseModel):
    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return x.notnull()


@process
class ScaleOffsetProcess(BaseModel):
    scale: float | None = None
    offset: float | None = None

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        if self.scale is not None:
            x = x * self.scale
        if self.offset is not None:
            x = x + self.offset
        return x


@domain_process(from_total_to_rate_of_change)
class FromTotalToRateOfChangeProcess(BaseModel):
    time_unit_seconds: int = 3600

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return from_total_to_rate_of_change(
            x=x, time_unit_seconds=self.time_unit_seconds
        )


@domain_process(from_rate_of_change_to_total)
class FromRateOfChangeToTotalProcess(BaseModel):
    time_unit_seconds: int = 3600

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return from_rate_of_change_to_total(
            x=x, time_unit_seconds=self.time_unit_seconds
        )


@process
class AggregateProcess(BaseModel):
    agg: Aggregation
    combiner_model: CoordCombinerModel

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return coord_combiner(self.combiner_model, context).agg(x, self.agg)


@domain_process(accumulator_differences)
class AccumulatorDifferencesProcess(BaseModel):
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return accumulator_differences(
            x=x,
            time_combiner=coord_combiner(self.time_combiner_model, context),
        )


@domain_process(resting_soc)
class RestingSocProcess(BaseModel):
    threshold: float = 0.01

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return resting_soc(x=x, threshold=self.threshold)


@process
class AbsoluteValueProcess(BaseModel):
    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return abs(x)


@process
class ForwardFillProcess(BaseModel):
    limit: int | None = None
    dim: str = Time.TIME_5MIN_UTC.value

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return x.ffill(limit=self.limit, dim=self.dim)


@process
class BackwardFillProcess(BaseModel):
    limit: int | None = None
    dim: str = Time.TIME_5MIN_UTC.value

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return x.bfill(limit=self.limit, dim=self.dim)


@domain_process(is_charging)
class IsChargingProcess(BaseModel):
    threshold: float = 0.01

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return is_charging(x=x, threshold=self.threshold)


@domain_process(is_discharging)
class IsDischargingProcess(BaseModel):
    threshold: float = 0.01

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return is_discharging(x=x, threshold=self.threshold)


@domain_process(is_idling)
class IsIdlingProcess(BaseModel):
    threshold: float = 0.01

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return is_idling(x=x, threshold=self.threshold)


@domain_process(availability)
class AvailabilityProcess(BaseModel):
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return availability(
            x=x, time_combiner=coord_combiner(self.time_combiner_model, context)
        )


@domain_process(remove_flat_lining)
class RemoveFlatLiningProcess(BaseModel):
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return remove_flat_lining(
            x=x, time_combiner=coord_combiner(self.time_combiner_model, context)
        )


@domain_process(event_change_to_in_event)
class EventChangeToInEventProcess(BaseModel):
    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return event_change_to_in_event(x=x)


@domain_process(agg_first)
class AggFirstProcess(BaseModel):
    time_combiner_model: CoordCombinerModel

    def __call__(self, *, x: xr.DataArray, context: ContextModel) -> xr.DataArray:
        return agg_first(
            x=x, time_combiner=coord_combiner(self.time_combiner_model, context)
        )
