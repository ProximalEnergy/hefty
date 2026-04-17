import xarray as xr
from kpi.base.enumeration import Attrs
from kpi.base.exception import MissingStaticDataError, NoDownloadedDataError
from kpi.base.protocol import DeviceProtocol
from kpi.infra.download.devices import download_device_df
from kpi.op.field_registry import FieldRegistry
from kpi.op.observer import observe
from kpi.op.util import assign_var


class DeviceSchema(FieldRegistry[DeviceProtocol]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        device_type_ids = set().union(
            *(self.get(field).device_type_ids() for field in self.plan)
        )
        device_df = download_device_df(
            dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
            list(device_type_ids),
        )
        if device_df.empty:
            raise NoDownloadedDataError(
                f"No device data found for device types: {device_type_ids}"
            )
        for field_name in self.plan:
            with observe(field_name=field_name):
                value = self.get(field_name).run(device_df=device_df)
                assign_var(
                    dataset,
                    field_name,
                    value,
                    exc=MissingStaticDataError,
                )
        return dataset
