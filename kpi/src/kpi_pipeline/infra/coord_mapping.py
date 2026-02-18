import datetime
from dataclasses import dataclass
from typing import Any, Self

import xarray as xr
from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.models import ContextModel, CoordCombinerModel
from kpi_pipeline.base.protocols import CoordCombinerProtocol, Implements
from kpi_pipeline.infra.device_grouper import DeviceGrouper, DeviceTreeProtocol
from kpi_pipeline.infra.time_grouper import TimeGrouper
from kpi_pipeline.infra.utils import broadcast, upsample, xarray_agg

coord_combiner_dec = Implements[CoordCombinerProtocol].decorator


class CoordCombinerAbstract:
    def _groupby_map(self, x: xr.DataArray) -> dict[str, Any]:
        raise NotImplementedError

    def group(self, x: xr.DataArray) -> xr.core.groupby.DataArrayGroupBy | xr.DataArray:
        group_map = self._groupby_map(x)
        if group_map:
            x = x.groupby(group_map)  # type: ignore
        return x

    def get_high_res_time_axis(self) -> Time:
        raise NotImplementedError

    def get_low_res_time_axis(self) -> Time:
        raise NotImplementedError

    def get_child_device_axis(self) -> DeviceType:
        raise NotImplementedError

    def get_parent_device_axis(self) -> DeviceType:
        raise NotImplementedError

    def dim(self) -> list[str]:
        raise NotImplementedError

    def agg(self, x: xr.DataArray, agg: Aggregation, **kwargs: Any) -> xr.DataArray:
        return xarray_agg(self.group(x=x), agg=agg, dim=self.dim(), **kwargs)


@coord_combiner_dec
@dataclass
class TimeCoordCombiner(CoordCombinerAbstract):
    high_res_time_axis: Time | None = None
    low_res_time_axis: Time | None = None
    time_zone: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None

    def _groupby_map(self, x: xr.DataArray) -> dict[str, Any]:
        group: dict[str, Any] = {}
        if self.high_res_time_axis is not None and self.low_res_time_axis is not None:
            if self.time_zone is None:
                raise ValueError("Time zone is required when converting time axes")
            grouper = TimeGrouper(
                from_time_axis=self.high_res_time_axis,
                to_time_axis=self.low_res_time_axis,
                time_zone=self.time_zone,
            )
            group[self.high_res_time_axis.value] = grouper
        return group

    def dim(self) -> list[str]:
        if self.high_res_time_axis is not None:
            return [self.high_res_time_axis.value]
        return []

    def get_high_res_time_axis(self) -> Time:
        if self.high_res_time_axis is not None:
            return self.high_res_time_axis
        raise ValueError("High resolution time axis is not set")

    def get_low_res_time_axis(self) -> Time:
        if self.low_res_time_axis is not None:
            return self.low_res_time_axis
        raise ValueError("Low resolution time axis is not set")

    def broadcast(self, x: xr.DataArray) -> xr.DataArray:
        if self.high_res_time_axis is not None and self.low_res_time_axis is not None:
            if self.time_zone is None:
                raise ValueError("Time zone is required when converting time axes")
            if self.start_date is None:
                raise ValueError("Start time is required when converting time axes")
            if self.end_date is None:
                raise ValueError("End time is required when converting time axes")
            x = upsample(
                x=x,
                low_frequency_time_axis=self.low_res_time_axis,
                high_frequency_time_axis=self.high_res_time_axis,
                time_zone=self.time_zone,
                start_date=self.start_date,
                end_date=self.end_date,
            )
        elif self.high_res_time_axis is not None:
            x = x.expand_dims(self.high_res_time_axis.value)
        return x

    @classmethod
    def from_axes(
        cls,
        context: ContextModel,
        high_res_time_axis: Time | None = None,
        low_res_time_axis: Time | None = None,
    ) -> Self:
        return cls(
            high_res_time_axis=high_res_time_axis,
            low_res_time_axis=low_res_time_axis,
            time_zone=context.project.time_zone,
            start_date=context.start_date,
            end_date=context.end_date,
        )


@coord_combiner_dec
@dataclass
class DeviceCoordCombiner(CoordCombinerAbstract):
    child_device_axis: DeviceType | None = None
    parent_device_axis: DeviceType | None = None
    device_tree: DeviceTreeProtocol | None = None

    def _groupby_map(self, x: xr.DataArray) -> dict[str, Any]:
        group: dict[str, Any] = {}
        if self.child_device_axis is not None and self.parent_device_axis is not None:
            if self.device_tree is None:
                raise ValueError("Device tree is required when converting device axes")
            grouper = DeviceGrouper(
                from_device_axis=self.child_device_axis,
                to_device_axis=self.parent_device_axis,
                device_tree=self.device_tree,
            )
            group[self.child_device_axis.name.lower()] = grouper
        return group

    def get_child_device_axis(self) -> DeviceType:
        if self.child_device_axis is not None:
            return self.child_device_axis
        raise ValueError("Child device axis is not set")

    def get_parent_device_axis(self) -> DeviceType:
        if self.parent_device_axis is not None:
            return self.parent_device_axis
        raise ValueError("Parent device axis is not set")

    def dim(self) -> list[str]:
        if self.child_device_axis is not None:
            return [self.child_device_axis.name.lower()]
        return []

    def broadcast(self, x: xr.DataArray) -> xr.DataArray:
        if self.child_device_axis is not None and self.parent_device_axis is not None:
            if self.device_tree is None:
                raise ValueError("Device tree is required when converting device axes")
            series = self.device_tree.parent_device_series(
                child_device_type=self.child_device_axis,
                parent_device_type=self.parent_device_axis,
            )
            mapped_coord = xr.DataArray(
                data=series.values,
                dims=[self.child_device_axis.name.lower()],
                coords={self.child_device_axis.name.lower(): series.index.values},
                name=self.parent_device_axis.name.lower(),
            )
            x = broadcast(x=x, mapped_coordinates=mapped_coord)
        elif self.child_device_axis is not None:
            x = x.expand_dims(self.child_device_axis.name.lower())
        return x

    @classmethod
    def from_axes(
        cls,
        context: ContextModel,
        parent_device_axis: DeviceType | None = None,
        child_device_axis: DeviceType | None = None,
    ) -> Self:
        return cls(
            parent_device_axis=parent_device_axis,
            child_device_axis=child_device_axis,
            device_tree=context.device_tree,
        )


@coord_combiner_dec
@dataclass
class CoordCombiner(CoordCombinerAbstract):
    time_combiner: TimeCoordCombiner
    device_combiner: DeviceCoordCombiner

    def _groupby_map(self, x: xr.DataArray) -> dict[str, Any]:
        group: dict[str, Any] = {}
        group.update(self.time_combiner._groupby_map(x))
        group.update(self.device_combiner._groupby_map(x))
        return group

    def dim(self) -> list[str]:
        dim = []
        dim.extend(self.time_combiner.dim())
        dim.extend(self.device_combiner.dim())
        return dim

    def get_high_res_time_axis(self) -> Time:
        return self.time_combiner.get_high_res_time_axis()

    def get_low_res_time_axis(self) -> Time:
        return self.time_combiner.get_low_res_time_axis()

    def get_child_device_axis(self) -> DeviceType:
        return self.device_combiner.get_child_device_axis()

    def get_parent_device_axis(self) -> DeviceType:
        return self.device_combiner.get_parent_device_axis()

    def broadcast(self, x: xr.DataArray) -> xr.DataArray:
        x = self.time_combiner.broadcast(x)
        x = self.device_combiner.broadcast(x)
        return x

    @classmethod
    def from_axes(
        cls,
        context: ContextModel,
        high_res_time_axis: Time | None = None,
        low_res_time_axis: Time | None = None,
        parent_device_axis: DeviceType | None = None,
        child_device_axis: DeviceType | None = None,
    ) -> Self:
        return cls(
            time_combiner=TimeCoordCombiner.from_axes(
                context, high_res_time_axis, low_res_time_axis
            ),
            device_combiner=DeviceCoordCombiner.from_axes(
                context, parent_device_axis, child_device_axis
            ),
        )


def coord_combiner(
    model: CoordCombinerModel, context: ContextModel
) -> CoordCombinerProtocol:
    return CoordCombiner.from_axes(
        context=context,
        high_res_time_axis=model.high_res_time_axis,
        low_res_time_axis=model.low_res_time_axis,
        parent_device_axis=model.parent_device_axis,
        child_device_axis=model.child_device_axis,
    )
