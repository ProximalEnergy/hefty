import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import NEW_NAME
from kpi.base.exception import KpiError
from kpi.base.protocol import device_protocol
from kpi.base.util import coord
from kpi.op.download.util import MarkdownDocModel

from core import models


@device_protocol
class DeviceHierarchyModel(MarkdownDocModel):
    child_device_type: DeviceTypeEnum
    parent_device_type: DeviceTypeEnum

    def device_type_ids(self) -> set[int]:
        return {self.child_device_type.value, self.parent_device_type.value}

    def run(self, device_df: pd.DataFrame) -> xr.DataArray:
        parent_filtered_df = device_df.loc[
            device_df.device_type_id == self.parent_device_type.value
        ]
        parent_device_level = int(
            parent_filtered_df.device_id_path.str.split(".").str.len().max() - 1
        )
        child_filtered_df = (
            device_df.loc[
                device_df.device_type_id == self.child_device_type.value,
                models.Device.device_id_path.name,
            ]
            .str.split(".", expand=True)
            .astype(int)
        )
        if parent_device_level >= child_filtered_df.shape[1]:
            raise KpiError(
                f"{repr(self.parent_device_type)} is not a parent of "
                f"{repr(self.child_device_type)}"
            )
        result = child_filtered_df.iloc[:, parent_device_level]
        return xr.DataArray(
            data=result.values,
            dims=[coord(self.child_device_type)],
            coords={
                coord(self.child_device_type): result.index.values,
            },
            attrs={
                NEW_NAME: coord(self.parent_device_type),
            },
        )
