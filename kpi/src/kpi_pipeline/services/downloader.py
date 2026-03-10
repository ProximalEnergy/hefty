from dataclasses import dataclass
from datetime import datetime
from typing import Self

import pandas as pd
import polars as pl
import xarray as xr
from core.crud.operational.sensor_types import get_sensor_types
from core.crud.project.data_expected import get_project_data_expected
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.devices import get_project_devices
from core.crud.project.events import get_windowed_events
from core.crud.project.tags import get_project_tags_v2
from core.database import with_db
from core.db_query import OutputType
from core.domain.statuses.statuses import get_status_time_series_failure_mode_ids
from core.enumerations import DeviceType, SensorType, TimeOffset
from kpi_pipeline.base.enums import UTC
from kpi_pipeline.base.models import (
    ContextModel,
    DeviceAttributeModel,
    ExpectedEnergyModel,
    OfflineEventModel,
    ProjectAttributeModel,
    SensorModel,
    StatusModel,
)
from kpi_pipeline.base.protocols import DataDownloadModelProtocol, DownloaderProtocol
from kpi_pipeline.infra.async_runner import run_in_loop
from kpi_pipeline.infra.data_access.pandas_to_xarray import (
    pandas_device_attributes_to_xarray,
    pandas_device_time_series_to_xarray,
    pandas_time_series_to_xarray,
)
from kpi_pipeline.infra.exceptions import NoDownloadedDataError
from pydantic import ConfigDict, validate_call
from sqlalchemy.orm import Session

from core import models

arbitrary_types = ConfigDict(arbitrary_types_allowed=True)
KPI_TAG_CHUNK_SIZE = 2_000

# helper functions


@validate_call(config=arbitrary_types)
async def _async_get_data_timeseries(
    *,
    project_db: Session,
    project_name_short: str,
    tags_chunk: pl.DataFrame,
    start: datetime,
    end: datetime,
):
    return await DataTimeseries(
        project_name_short=project_name_short,
        query_start=start,
        query_end=end,
        max_lookback_period=TimeOffset.ONE_HOUR,
        project_db=project_db,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_chunk,
        ensure_full_range=True,
        dangerous_pagination_override=False,
    ).get_all()


# implementations of downloader protocols


@dataclass
class ProjectAttributesDownloader(DownloaderProtocol[ProjectAttributeModel]):
    map: dict[str, ProjectAttributeModel]
    project: models.Project

    @classmethod
    def from_download(
        cls, map: dict[str, ProjectAttributeModel], context: ContextModel
    ) -> Self:
        return cls(map=map, project=context.project)

    def data_array(self, model: ProjectAttributeModel) -> xr.DataArray:
        return xr.DataArray(getattr(self.project, model.source_field_name))


@dataclass
class DeviceAttributesDownloader(DownloaderProtocol[DeviceAttributeModel]):
    map: dict[str, DeviceAttributeModel]
    data_raw: pd.DataFrame

    @classmethod
    def from_download(
        cls, map: dict[str, DeviceAttributeModel], context: ContextModel
    ) -> Self:
        device_type_ids = [
            device_attribute.device_type.value for device_attribute in map.values()
        ]

        devices = get_project_devices(
            device_type_ids=device_type_ids,
        ).get(schema=context.project.name_short, output_type=OutputType.PANDAS)

        data_raw = devices.set_index(models.Device.device_id.name)

        return cls(map=map, data_raw=data_raw)

    def data_array(self, model: DeviceAttributeModel) -> xr.DataArray:
        return pandas_device_attributes_to_xarray(
            series=self.data_raw.loc[
                self.data_raw.device_type_id == model.device_type.value,
                model.source_field_name,
            ],
            device_type=model.device_type,
        )


class TimeSeriesDownloaderAbstract[T: DataDownloadModelProtocol]:
    def device_type(self, model: T) -> DeviceType:
        raise NotImplementedError("Subclasses must implement this method")

    def filtered_pandas(self, model: T) -> pd.DataFrame:
        raise NotImplementedError("Subclasses must implement this method")

    def data_array(self, model: T) -> xr.DataArray:
        filtered = self.filtered_pandas(model)
        if model.project_level:
            if filtered.empty:
                raise NoDownloadedDataError(
                    "Filtered dataframe for project level time series is empty"
                )
            if len(filtered.columns) > 1:
                raise ValueError(
                    f"Expected 1 column for project level time series, got {len(filtered.columns)}"
                )
            return pandas_time_series_to_xarray(series=filtered.iloc[:, 0])
        else:
            return pandas_device_time_series_to_xarray(
                dataframe=filtered, device_type=self.device_type(model)
            )


@dataclass
class ExpectedEnergyDownloader(
    TimeSeriesDownloaderAbstract[ExpectedEnergyModel],
    DownloaderProtocol[ExpectedEnergyModel],
):
    map: dict[str, ExpectedEnergyModel]
    data_raw: pd.DataFrame

    @classmethod
    def from_download(
        cls, map: dict[str, ExpectedEnergyModel], context: ContextModel
    ) -> Self:
        expected_metric_ids = [
            expected_energy_model.expected_metric_id
            for expected_energy_model in map.values()
        ]
        device_types = set(model.device_type for model in map.values())
        all_device_ids = []
        for device_type in device_types:
            all_device_ids.extend(
                context.device_tree.device_ids(device_type=device_type)
            )
        model_list = get_project_data_expected(
            expected_metric_ids=expected_metric_ids,
            device_ids=all_device_ids,
            start=pd.to_datetime(context.start_time_utc()).to_pydatetime(),
            end=pd.to_datetime(context.end_time_utc()).to_pydatetime(),
        ).get(output_type=OutputType.PANDAS, schema=context.project.name_short)

        expected_df = model_list.set_index(models.DataExpected.time.name)
        return cls(map=map, data_raw=expected_df)

    def device_type(self, model: ExpectedEnergyModel) -> DeviceType:
        return model.device_type

    def filtered_pandas(self, model: ExpectedEnergyModel) -> pd.DataFrame:
        filtered_df = self.data_raw.loc[
            self.data_raw.expected_metric_id == model.expected_metric_id
        ]
        pivoted_df = filtered_df.pivot_table(
            index=models.DataExpected.time.name,
            columns=models.DataExpected.device_id.name,
            values=models.DataExpected.value.name,
        )
        return pivoted_df


def _set_index_and_columns(data_raw: pd.DataFrame) -> pd.DataFrame:
    if data_raw.empty:
        raise NoDownloadedDataError("Dataframe is empty")
    data_raw.index = data_raw.index.tz_convert(UTC).tz_localize(None)  # type: ignore
    data_raw.columns = data_raw.columns.astype(int)
    return data_raw


def _get_tag_df(
    sensor_type_id_list: list[int], project: models.Project
) -> pd.DataFrame:
    tags = get_project_tags_v2(
        sensor_type_ids=sensor_type_id_list,
    )
    return tags.get(schema=project.name_short, output_type=OutputType.PANDAS).set_index(
        models.Tag.tag_id.name
    )[[models.Tag.sensor_type_id.name, models.Tag.device_id.name]]


def _get_tag_polars(
    *, sensor_type_id_list: list[int], project: models.Project
) -> pl.DataFrame:
    return get_project_tags_v2(
        sensor_type_ids=sensor_type_id_list,
    ).get(
        schema=project.name_short,
        output_type=OutputType.POLARS,
    )


def _iter_tag_chunks(*, tags: pl.DataFrame) -> list[pl.DataFrame]:
    return [
        tags.slice(i, KPI_TAG_CHUNK_SIZE)
        for i in range(0, len(tags), KPI_TAG_CHUNK_SIZE)
    ]


def _tag_df_from_tags_polars(*, tags: pl.DataFrame) -> pd.DataFrame:
    return (
        tags.select(
            [
                models.Tag.tag_id.name,
                models.Tag.sensor_type_id.name,
                models.Tag.device_id.name,
            ]
        )
        .to_pandas()
        .set_index(models.Tag.tag_id.name)
    )


def _get_sensor_types(sensor_type_id_list: list[int]):
    sensor_types = get_sensor_types(
        sensor_type_ids=sensor_type_id_list,
    ).get(schema=None, output_type=OutputType.PANDAS)
    return sensor_types.set_index(models.SensorType.sensor_type_id.name)[
        models.SensorType.device_type_id.name
    ]


def _get_existing_columns_df(
    tag_df: pd.DataFrame, data_raw: pd.DataFrame, sensor_type: SensorType
) -> pd.DataFrame:
    desired_tags = tag_df[tag_df[models.Tag.sensor_type_id.name] == sensor_type.value]
    existing_columns = [
        tag_id for tag_id in desired_tags.index if tag_id in data_raw.columns
    ]
    if len(existing_columns) == 0:
        raise NoDownloadedDataError(
            f"No downloaded tags for sensor type {repr(sensor_type)}"
        )
    filtered_df = data_raw[existing_columns]
    if filtered_df.empty:
        raise NoDownloadedDataError("Filtered dataframe is empty")
    return filtered_df


@dataclass
class TimeSeriesDownloader(
    TimeSeriesDownloaderAbstract[SensorModel], DownloaderProtocol[SensorModel]
):
    map: dict[str, SensorModel]
    data_raw: pd.DataFrame
    tag_df: pd.DataFrame
    sensor_type_to_device_type_series: pd.Series

    @classmethod
    def from_download(cls, map: dict[str, SensorModel], context: ContextModel) -> Self:
        project = context.project
        start = context.start_date
        # add 5 minutes to get first time step of the following day
        end = context.end_date + pd.Timedelta(minutes=5)
        sensor_type_id_list = [sensor.sensor_type.value for sensor in map.values()]
        tags_polars = _get_tag_polars(
            sensor_type_id_list=sensor_type_id_list,
            project=project,
        )
        if tags_polars.is_empty():
            raise NoDownloadedDataError(
                "No tags found for sensor types "
                f"{[s.sensor_type for s in map.values()]}"
            )

        with with_db(schema=project.name_short) as project_db:
            data_timeseries_chunks = []
            for tags_chunk in _iter_tag_chunks(tags=tags_polars):
                data_timeseries_chunks.append(
                    run_in_loop(
                        _async_get_data_timeseries(
                            project_db=project_db,
                            project_name_short=project.name_short,
                            tags_chunk=tags_chunk,
                            start=start,  # type: ignore
                            end=end,  # type: ignore
                        )
                    )
                )
        data_raw = pd.concat(
            [
                chunk.df.to_pandas().set_index(models.DataTimeseries.time.name)
                for chunk in data_timeseries_chunks
            ],
            axis=1,
        )
        data_raw = _set_index_and_columns(data_raw)

        # Now we have a dataframe with time on the index and tag ids as the columns

        # For each tag, get corresponding sensor type and device id

        tag_df = _tag_df_from_tags_polars(tags=tags_polars)

        # For each sensor type, get corresponding device type

        sensor_type_to_device_type_series = _get_sensor_types(sensor_type_id_list)

        return cls(
            map=map,
            data_raw=data_raw,
            tag_df=tag_df,
            sensor_type_to_device_type_series=sensor_type_to_device_type_series,
        )

    def device_type(self, model: SensorModel) -> DeviceType:
        return DeviceType(
            self.sensor_type_to_device_type_series[model.sensor_type.value]
        )

    def filtered_pandas(self, model: SensorModel) -> pd.DataFrame:
        filtered_df = _get_existing_columns_df(
            self.tag_df, self.data_raw, model.sensor_type
        )

        filtered_df_renamed = filtered_df.rename(
            columns=self.tag_df.device_id.to_dict()
        )
        if model.aggregation is not None:
            filtered_df_renamed = (
                filtered_df_renamed.T.groupby(level=0).agg(model.aggregation.value).T
            )
        return filtered_df_renamed


@dataclass
class StatusTimeSeriesDownloader(
    TimeSeriesDownloaderAbstract[StatusModel], DownloaderProtocol[StatusModel]
):
    map: dict[str, StatusModel]
    data_raw: pd.DataFrame
    tag_df: pd.DataFrame
    sensor_type_to_device_type_series: pd.Series

    @classmethod
    def from_download(cls, map: dict[str, StatusModel], context: ContextModel) -> Self:
        project = context.project

        with with_db(schema=project.name_short) as project_db:
            data_timeseries = run_in_loop(
                get_status_time_series_failure_mode_ids(
                    project_db=project_db,
                    start=context.start_time_local(),
                    end=context.end_time_local(),
                    project=project,
                    sensor_type_ids=[
                        sensor.sensor_type.value for sensor in map.values()
                    ],
                    get_all=True,
                )
            )

        data_raw = pd.DataFrame(data_timeseries)
        if data_raw.empty:
            raise NoDownloadedDataError(
                f"Dataframe is empty for sensor types {[repr(sensor.sensor_type) for sensor in map.values()]}"
            )
        data_raw = data_raw.set_index("index")
        data_raw = _set_index_and_columns(data_raw)

        # convert to nullable integers
        data_raw = data_raw.astype("Int32")

        # Now we have a dataframe with time on the index and tag ids as the columns

        # For each tag, get corresponding sensor type and device id

        sensor_type_id_list = [sensor.sensor_type.value for sensor in map.values()]

        tag_df = _get_tag_df(sensor_type_id_list, project)

        # For each sensor type, get corresponding device type

        sensor_type_to_device_type_series = _get_sensor_types(sensor_type_id_list)

        return cls(
            map=map,
            data_raw=data_raw,
            tag_df=tag_df,
            sensor_type_to_device_type_series=sensor_type_to_device_type_series,
        )

    def device_type(self, model: StatusModel) -> DeviceType:
        return DeviceType(
            self.sensor_type_to_device_type_series[model.sensor_type.value]
        )

    def filtered_pandas(self, model: StatusModel) -> pd.DataFrame:
        filtered_df = _get_existing_columns_df(
            self.tag_df, self.data_raw, model.sensor_type
        )

        failure_df = filtered_df.isin(model.failure_modes).astype(bool)

        # This grouping checks to see if any sensor type within the same device matches the
        # provided failure modes.

        failure_df_grouped = (
            failure_df.T.groupby(self.tag_df.device_id.to_dict()).any().T
        ).astype(bool)

        return failure_df_grouped


@dataclass
class OfflineEventDownloader(
    TimeSeriesDownloaderAbstract[OfflineEventModel],
    DownloaderProtocol[OfflineEventModel],
):
    map: dict[str, OfflineEventModel]
    data_raw: pd.DataFrame

    @classmethod
    def from_download(
        cls, map: dict[str, OfflineEventModel], context: ContextModel
    ) -> Self:
        start = context.start_time_local()
        end = context.end_time_local()
        events = get_windowed_events(
            start=start,
            end=end,
            deep=False,
            include_underperformance=False,
            failure_mode_ids=None,
            device_type_ids=list(
                set(model.device_type.value for model in map.values())
            ),
        )

        df_events = events.get(
            schema=context.project.name_short, output_type=OutputType.PANDAS
        )
        # only keep the necessary columns
        df_events = df_events[["device_id", "time_start", "time_end", "device_type_id"]]
        # clip start time to the start of the context
        df_events["time_start"] = df_events["time_start"].clip(lower=start)  # type: ignore[call-overload]
        # if time end is after end of context, set it to NaN
        df_events["time_end"] = df_events["time_end"].where(  # type: ignore[call-overload]
            df_events["time_end"] <= end, pd.NaT
        )
        return cls(map=map, data_raw=df_events)

    def device_type(self, model: OfflineEventModel) -> DeviceType:
        return model.device_type

    def filtered_pandas(self, model: OfflineEventModel) -> pd.DataFrame:
        filtered = self.data_raw.loc[
            self.data_raw.device_type_id == model.device_type.value
        ]
        start = filtered.assign(present=1.0).pivot_table(
            index="time_start", columns="device_id", values="present", aggfunc="sum"
        )
        end = filtered.assign(present=-1.0).pivot_table(
            index="time_end", columns="device_id", values="present", aggfunc="sum"
        )
        event_change_status = start.add(end, fill_value=0)
        return event_change_status
