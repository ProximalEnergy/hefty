import datetime
import uuid
from typing import Annotated, Any

import numpy as np
import pandas as pd
from core.enumerations import DeviceType, SensorType
from dotenv import load_dotenv
from kpi_pipeline.base.enums import Aggregation, DataType, Time
from kpi_pipeline.base.protocols import DataDownloadModelProtocol, Implements
from kpi_pipeline.infra.device_manager import DeviceTree
from kpi_pipeline.infra.utils import pandas_timestamp_to_datetime64_utc
from pydantic import BaseModel, BeforeValidator, Field

from core import models

NANOSECONDS = "ns"

# Load environment variables from .env file
load_dotenv()

data_download_model = Implements[DataDownloadModelProtocol].decorator


@data_download_model
class ProjectAttributeModel(BaseModel):
    source_field_name: str
    scale: float | None = None
    offset: float | None = None
    dtype: DataType = DataType.FLOAT
    fill_value: Any | None = None

    project_level: bool = Field(default=True, init=False)


@data_download_model
class DeviceAttributeModel(BaseModel):
    device_type: DeviceType
    source_field_name: str
    scale: float | None = None
    offset: float | None = None
    dtype: DataType = DataType.FLOAT
    fill_value: Any | None = None

    project_level: bool = Field(default=False, init=False)


@data_download_model
class SensorModel(BaseModel):
    sensor_type: SensorType
    project_level: bool = False
    scale: float | None = None
    offset: float | None = None
    dtype: DataType = DataType.FLOAT
    aggregation: Aggregation | None = None
    fill_value: Any | None = None


@data_download_model
class ExpectedEnergyModel(BaseModel):
    expected_metric_id: int
    device_type: DeviceType
    project_level: bool = False
    scale: float | None = None
    offset: float | None = None
    dtype: DataType = DataType.FLOAT
    fill_value: Any | None = None


@data_download_model
class StatusModel(BaseModel):
    sensor_type: SensorType
    failure_modes: list[int]
    project_level: bool = False
    dtype: DataType = DataType.BOOL
    fill_value: Any | None = False
    scale: float | None = Field(default=None, init=None)
    offset: float | None = Field(default=None, init=None)


@data_download_model
class PvLibModel(BaseModel):
    field_name: str
    project_level: bool = True
    dtype: DataType = DataType.FLOAT
    fill_value: Any | None = None
    scale: float | None = None
    offset: float | None = None


# 1. Define the reusable coercion function
def to_finite_float(value: Any) -> Any:
    """Converts NaN, Inf, and non-numeric values to None. Returns finite numeric values unchanged."""
    if np.isfinite(value):
        return value
    return None


# Define a custom type alias for clarity and reuse
FiniteFloat = Annotated[float | None, BeforeValidator(to_finite_float)]


class DeviceDataJson(BaseModel):
    device_values: dict[int, FiniteFloat]

    model_config = {
        "arbitrary_types_allowed": True,  # Allow numpy types
    }


class KPIDataRow(BaseModel):
    """
    Pydantic model for validating and coercing KPI data rows.
    """

    date: datetime.date
    project_id: uuid.UUID
    kpi_type_id: int
    device_data_json: DeviceDataJson | None
    project_data: float
    version: str

    model_config = {
        "arbitrary_types_allowed": True,  # Allow numpy types
    }


class KPIMetadata(BaseModel):
    project_var: str
    device_var: str | None = None
    version: str
    scale: float | None = None
    offset: float | None = None


class ContextModel(BaseModel):
    project: models.Project
    start_date: datetime.date
    end_date: datetime.date
    device_tree: DeviceTree

    model_config = {
        "arbitrary_types_allowed": True,  # Allow core.models.Project type
    }

    def start_time_local(self) -> pd.Timestamp:
        return pd.Timestamp(self.start_date, tz=self.project.time_zone)

    def end_time_local(self) -> pd.Timestamp:
        return pd.Timestamp(self.end_date, tz=self.project.time_zone)

    def start_time_utc(self) -> np.datetime64:
        return pandas_timestamp_to_datetime64_utc(self.start_time_local())

    def end_time_utc(self) -> np.datetime64:
        return pandas_timestamp_to_datetime64_utc(self.end_time_local())


class CoordCombinerModel(BaseModel):
    high_res_time_axis: Time | None = None
    low_res_time_axis: Time | None = None
    child_device_axis: DeviceType | None = None
    parent_device_axis: DeviceType | None = None
