import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs
from kpi.base.protocol import DeviceAttributeProtocol
from kpi.base.util import coord
from kpi.domain.util import scale_offset
from kpi.infra.download.devices import download_device_df
from kpi.service.field import Field, NoInputs
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.util import assign_var
from pydantic import BaseModel


class DeviceAttributeModel(BaseModel, NoInputs):
    device_type: DeviceType
    source_field_name: str
    scale: float | None
    offset: float | None

    def run(self, data_raw: pd.DataFrame) -> xr.DataArray:
        series = data_raw.loc[
            data_raw.device_type_id == self.device_type.value,
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


class DeviceAttributeSchema(FieldRegistry[DeviceAttributeProtocol]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        device_type_ids = set[int](
            self.get(field).device_type.value for field in self.plan
        )
        data_raw = download_device_df(
            dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
            list(device_type_ids),
        )
        for field_name in self.plan:
            with observe(field_name=field_name):
                value = self.get(field_name).run(data_raw=data_raw)
                assign_var(
                    dataset,
                    field_name,
                    value,
                )
        return dataset
