import xarray as xr
from kpi.base.enumeration import Attrs
from kpi.base.exception import MissingStaticDataError, NoDownloadedDataError
from kpi.base.protocol import DeviceProtocol
from kpi.infra.download.devices import download_device_df
from kpi.op.observer import observe
from kpi.op.plan import FieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var


class DeviceSchema(SchemaAbstract[DeviceProtocol]):
    def run(self, dataset: xr.Dataset, plan: FieldPlan) -> xr.Dataset:
        device_type_ids = set[int]().union(
            *(self.map[field].device_type_ids() for field in plan.root.keys())
        )
        device_df = download_device_df(
            dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
            list(device_type_ids),
        )
        if device_df.empty:
            raise NoDownloadedDataError(
                f"No device data found for device types: {device_type_ids}"
            )
        for field_name in plan.root.keys():
            with observe(field_name=field_name):
                value = self.map[field_name].run(device_df=device_df)
                assign_var(dataset, field_name, value, exc=MissingStaticDataError)
        return dataset
