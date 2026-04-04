import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs
from kpi.base.exception import NoDownloadedDataError
from kpi.base.util import coord
from kpi.infra.download.devices import download_device_df
from kpi.service.field import Field, NoInputs
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.util import assign_var
from pydantic import BaseModel

from core import models


class DeviceHierarchyModel(BaseModel, NoInputs):
    child_device_type: DeviceType
    parent_device_type: DeviceType


def device_hierarchy_field(
    child_device_type: DeviceType,
    parent_device_type: DeviceType,
) -> Field[DeviceHierarchyModel]:
    return Field[DeviceHierarchyModel](
        DeviceHierarchyModel(
            child_device_type=child_device_type, parent_device_type=parent_device_type
        )
    )


class DeviceHierarchySchema(FieldRegistry[DeviceHierarchyModel]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        parent_device_type_ids = set[int](
            self.get(field).parent_device_type.value for field in self.plan
        )
        child_device_type_ids = set[int](
            self.get(field).child_device_type.value for field in self.plan
        )
        all_device_type_ids = parent_device_type_ids.union(child_device_type_ids)

        device_df = download_device_df(
            dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
            list(all_device_type_ids),
        )

        if device_df.empty:
            raise NoDownloadedDataError(
                "No devices found for project "
                f"{dataset.attrs[Attrs.PROJECT_NAME_SHORT.value]}"
            )

        device_level_map = {}
        for device_type_id in parent_device_type_ids:
            filtered_df = device_df.loc[device_df.device_type_id == device_type_id]
            device_level_map[device_type_id] = int(
                filtered_df.device_id_path.str.split(".").str.len().max() - 1
            )

        for field_name in self.plan:
            with observe(field_name=field_name):
                model = self.get(field_name)
                parent_device_level = device_level_map[model.parent_device_type.value]
                filtered_df = (
                    device_df.loc[
                        device_df.device_type_id == model.child_device_type.value,
                        models.Device.device_id_path.name,
                    ]
                    .str.split(".", expand=True)
                    .astype(int)
                )
                if parent_device_level >= filtered_df.shape[1]:
                    raise ValueError(
                        f"{repr(model.parent_device_type)} is not a parent of "
                        f"{repr(model.child_device_type)}"
                    )
                result = filtered_df.iloc[:, parent_device_level]
                assign_var(
                    dataset,
                    field_name,
                    xr.DataArray(
                        data=result.values,
                        dims=[coord(model.child_device_type)],
                        coords={
                            coord(model.child_device_type): result.index.values,
                        },
                    ),
                )

        return dataset
