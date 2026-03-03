from typing import ClassVar, Self

import xarray as xr
from kpi_pipeline.base.models import (
    ContextModel,
    DeviceAttributeModel,
    ExpectedEnergyModel,
    ProjectAttributeModel,
    SensorModel,
    StatusModel,
)
from kpi_pipeline.base.protocols import (
    CalcProtocol,
    DataDownloadModelProtocol,
    DownloaderProtocol,
    Implements,
    ObserverProtocol,
    ProcessProtocol,
    TransformProtocol,
)
from kpi_pipeline.infra.utils import (
    assign_var,
    filter_by_time_range_utc,
    select,
)
from kpi_pipeline.services.action.utils import (
    is_empty,
    is_identity,
    through_outputs,
)
from kpi_pipeline.services.calc import CalcProcess, SelectCalc
from kpi_pipeline.services.downloader import (
    DeviceAttributesDownloader,
    ExpectedEnergyDownloader,
    ProjectAttributesDownloader,
    StatusTimeSeriesDownloader,
    TimeSeriesDownloader,
)
from pydantic import BaseModel

transform = Implements[TransformProtocol].decorator


@transform
class IdentityTransform(BaseModel):
    pass_through: ClassVar[bool] = True

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> xr.Dataset:
        return dataset

    def nominal_outputs(self) -> list[str]:
        return []

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        return outputs

    def trim(self, *, outputs: list[str] = []) -> Self:
        return self


class SelectFieldsTransform(TransformProtocol):
    pass_through = False

    def __init__(self, *, field_names: list[str]):
        self.field_names = field_names

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ):
        ds = xr.Dataset()
        for field_name in self.field_names:
            with assign_var(
                observer=observer,
                var=field_name,
                dataset=ds,
            ) as result:
                result.value = select(dataset, field_name)
        return ds

    def nominal_outputs(self) -> list[str]:
        return self.field_names

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        return list(set(outputs).intersection(self.field_names))

    def trim(self, *, outputs: list[str] = []) -> Self:
        return self.__class__(
            field_names=self.expected_inputs(outputs=outputs),
        )


class CalcTransform(TransformProtocol):
    def __init__(
        self,
        *,
        field: str,
        calculation: CalcProtocol | None = None,
        pass_through: bool = True,
    ):
        self.field = field
        self.calculation = calculation
        self._pass_through = pass_through

    @property
    def pass_through(self) -> bool:
        return self._pass_through

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ):
        if self.pass_through:
            ds = dataset
        else:
            ds = xr.Dataset(attrs=dataset.attrs)
        if self.calculation is not None:
            with assign_var(
                observer=observer,
                var=self.field,
                dataset=ds,
                dtype=self.calculation.output_dtype,
            ) as result:
                result.value = self.calculation(dataset=dataset, context=context)
        return ds

    def nominal_outputs(self) -> list[str]:
        if self.calculation is None:
            return []
        return [self.field]

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        if self.pass_through:
            inputs = set(outputs)
        else:
            inputs = set()

        if self.calculation is None or self.field not in outputs:
            return list(inputs)

        return list(inputs - {self.field} | set(self.calculation.expected_inputs()))

    def trim(self, *, outputs: list[str] = []) -> Self:
        if self.field in outputs:
            return self.__class__(
                field=self.field,
                calculation=self.calculation,
                pass_through=self.pass_through,
            )
        else:
            return self.__class__(
                field=self.field, calculation=None, pass_through=self.pass_through
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.field})"


class TransformList(TransformProtocol):
    def __init__(
        self,
        steps: list[TransformProtocol],
    ):
        self.steps = steps

    @property
    def pass_through(self) -> bool:
        return all(transform.pass_through for transform in self.steps)

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ):
        for func in self.steps:
            dataset = func(dataset=dataset, context=context, observer=observer)
        return dataset

    def nominal_outputs(self) -> list[str]:
        previous_outputs = []
        for transform in self.steps:
            previous_outputs = through_outputs(
                transform=transform, previous_outputs=previous_outputs
            )
        return previous_outputs

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        for transform in reversed(self.steps):
            outputs = transform.expected_inputs(outputs=outputs)
        return outputs

    def trim(
        self,
        *,
        outputs: list[str] = [],
    ) -> Self:
        steps_backwards = []
        for transform in reversed(self.steps):
            trimmed_transform = transform.trim(outputs=outputs)
            if not is_identity(trimmed_transform) or (
                hasattr(trimmed_transform, "skippable")
                and not trimmed_transform.skippable
            ):
                steps_backwards.append(trimmed_transform)
                outputs = trimmed_transform.expected_inputs(outputs=outputs)
        return self.__class__(steps=list(reversed(steps_backwards)))

    @classmethod
    def from_calc_map(
        cls,
        calc_map: dict[str, CalcProtocol],
    ) -> Self:
        steps: list[TransformProtocol] = [
            CalcTransform(
                field=field,
                calculation=calculation,
                pass_through=True,
            )
            for field, calculation in calc_map.items()
        ]
        return cls(steps=steps)


class MergeTransform(TransformProtocol):
    def __init__(
        self,
        transforms: list[TransformProtocol],
        pass_through: bool = False,
    ):
        self.transforms = transforms
        self._pass_through = pass_through
        self._check_disjoint_outputs()

    @property
    def pass_through(self) -> bool:
        return self._pass_through

    def _check_disjoint_outputs(self):
        if any(transform.pass_through for transform in self.transforms):
            raise ValueError("The transforms cannot be pass through")
        number_of_outputs = sum(
            len(transform.nominal_outputs()) for transform in self.transforms
        )
        if number_of_outputs != len(self.nominal_outputs()):
            raise ValueError("The outputs of the transforms are not disjoint")

    def nominal_outputs(self) -> list[str]:
        return list(
            set().union(*[transform.nominal_outputs() for transform in self.transforms])
        )

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> xr.Dataset:
        if self.pass_through:
            dataset_list = [dataset.drop_vars(self.nominal_outputs(), errors="ignore")]
        else:
            dataset_list = [xr.Dataset(attrs=dataset.attrs)]
        for transform in self.transforms:
            dataset_list.append(
                transform(dataset=dataset.copy(), context=context, observer=observer)
            )
        return xr.merge(dataset_list, compat="no_conflicts")

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        return list(
            set().union(
                *[
                    transform.expected_inputs(outputs=outputs)
                    for transform in self.transforms
                ]
            )
        )

    def trim(self, *, outputs: list[str] = []) -> Self:
        transforms = []
        for transform in self.transforms:
            transform = transform.trim(outputs=outputs)
            if not is_empty(transform):
                transforms.append(transform)
        return self.__class__(
            transforms=transforms,
            pass_through=self.pass_through,
        )

    @classmethod
    def from_calc_map(
        cls,
        calc_map: dict[str, CalcProtocol],
        pass_through: bool = False,
    ) -> TransformProtocol:
        transforms: list[TransformProtocol] = [
            CalcTransform(
                field=field,
                calculation=calculation,
                pass_through=False,
            )
            for field, calculation in calc_map.items()
        ]
        return cls(transforms=transforms, pass_through=pass_through)

    @classmethod
    def from_process_map(
        cls,
        process_map: dict[str, ProcessProtocol],
        pass_through: bool = False,
    ) -> TransformProtocol:
        transforms: list[TransformProtocol] = [
            CalcTransform(
                field=field,
                calculation=CalcProcess(calc=SelectCalc(var=field), process=process),
                pass_through=False,
            )
            for field, process in process_map.items()
        ]
        return cls(transforms=transforms, pass_through=pass_through)


class DownloadTransformAbstract[T](TransformProtocol):
    pass_through = False
    _downloader_class: type[DownloaderProtocol]

    def __init__(
        self,
        *,
        map: dict[str, DataDownloadModelProtocol],
    ):
        self.map = map

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> xr.Dataset:
        downloader = None
        with observer.watch():
            downloader = self._downloader_class.from_download(
                map=self.map, context=context
            )
        if downloader is None:
            return dataset  # type: ignore
        for field_name, model in self.map.items():
            with assign_var(
                observer=observer,
                var=field_name,
                dataset=dataset,
                dtype=model.dtype,
                scale=model.scale,
                offset=model.offset,
                fill_value=model.fill_value,
            ) as result:
                result.value = downloader.data_array(model=model)
        return dataset

    def nominal_outputs(self, previous_outputs: list[str] = []) -> list[str]:
        return list(set(previous_outputs) | set(self.map.keys()))

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        return list(set(outputs) - set(self.map.keys()))

    def trim(self, *, outputs: list[str] = []) -> Self:
        return self.__class__(
            map={
                field_name: value
                for field_name, value in self.map.items()
                if field_name in outputs
            }
        )


class DownloadDeviceAttributesTransform(
    DownloadTransformAbstract[DeviceAttributeModel], TransformProtocol
):
    _downloader_class = DeviceAttributesDownloader


class DownloadProjectAttributesTransform(
    DownloadTransformAbstract[ProjectAttributeModel], TransformProtocol
):
    _downloader_class = ProjectAttributesDownloader


class DownloadTimeSeriesTransform(
    DownloadTransformAbstract[SensorModel], TransformProtocol
):
    _downloader_class = TimeSeriesDownloader


class DownloadExpectedEnergyTransform(
    DownloadTransformAbstract[ExpectedEnergyModel], TransformProtocol
):
    _downloader_class = ExpectedEnergyDownloader


class DownloadStatusTimeSeriesTransform(
    DownloadTransformAbstract[StatusModel], TransformProtocol
):
    _downloader_class = StatusTimeSeriesDownloader


@transform
class TrimTimeRangeTransform(IdentityTransform):
    skippable: ClassVar[bool] = False

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> xr.Dataset:
        return filter_by_time_range_utc(
            x=dataset,
            start_time_utc=context.start_time_utc(),
            end_time_utc=context.end_time_utc(),
        )
