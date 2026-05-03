import datetime
from uuid import UUID

import pandas as pd
import xarray as xr
from pydantic import BaseModel


class ContextModel(BaseModel):
    project_id: UUID
    project_name_short: str
    start_date: datetime.date
    end_date: datetime.date
    time_zone: str

    @property
    def start_tz_aware(self) -> pd.Timestamp:
        return pd.Timestamp(self.start_date, tz=self.time_zone)

    @property
    def end_tz_aware(self) -> pd.Timestamp:
        return pd.Timestamp(self.end_date, tz=self.time_zone)


def get_context(dataset: xr.Dataset) -> ContextModel:
    return ContextModel.model_validate(dataset.attrs)
