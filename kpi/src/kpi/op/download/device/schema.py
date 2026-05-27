from typing import Annotated, Literal

import pydantic as pyd
import xarray as xr
from kpi.base.context import get_context
from kpi.base.exception import MissingStaticDataError, NoDownloadedDataError
from kpi.base.protocol import schema_protocol
from kpi.infra.download.devices import download_device_df
from kpi.op.download.device.attribute import DeviceAttributeModel
from kpi.op.download.device.hierarchy import DeviceHierarchyModel
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var
from pydantic import BaseModel

DeviceNode = Annotated[
    DeviceAttributeModel | DeviceHierarchyModel, pyd.Field(discriminator="kind")
]


@schema_protocol
class DeviceSchema(BaseModel, SchemaAbstract[DeviceNode]):
    kind: Literal["DeviceSchema"] = "DeviceSchema"
    map: dict[str, DeviceNode]

    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        field_names = plan.outputs()
        device_type_ids = set[int]().union(
            *(self.map[field_name].device_type_ids() for field_name in field_names)
        )

        context = get_context(dataset)

        device_df = download_device_df(
            context.project_name_short,
            list(device_type_ids),
        )
        if device_df.empty:
            raise NoDownloadedDataError(
                f"No device data found for device types: {device_type_ids}"
            )
        for field_name in field_names:
            with observe(field_name=field_name):
                value = self.map[field_name].run(device_df=device_df)
                assign_var(dataset, field_name, value, exc=MissingStaticDataError)
        return dataset
