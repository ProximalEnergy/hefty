import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.util import coord
from kpi.domain.util import scale_offset
from kpi.op.field import Field, NoInputs
from pydantic import BaseModel


class DeviceAttributeModel(BaseModel, NoInputs):
    device_type: DeviceType
    source_field_name: str
    scale: float | None
    offset: float | None

    def device_type_ids(self) -> set[int]:
        return {self.device_type.value}

    def run(self, device_df: pd.DataFrame) -> xr.DataArray:
        series = device_df.loc[
            device_df.device_type_id == self.device_type.value,
            self.source_field_name,
        ]
        device_type_name = coord(self.device_type)
        value = xr.DataArray(
            data=series.values,
            dims=[device_type_name],
            coords={
                device_type_name: series.index.values,
            },
        )
        return scale_offset(value, scale=self.scale, offset=self.offset)


def device_attribute_field(
    device_type: DeviceType,
    source_field_name: str,
    scale: float | None = None,
    offset: float | None = None,
) -> Field[DeviceAttributeModel]:
    return Field[DeviceAttributeModel](
        DeviceAttributeModel(
            device_type=device_type,
            source_field_name=source_field_name,
            scale=scale,
            offset=offset,
        )
    )
