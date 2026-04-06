import xarray as xr
from kpi.base.enumeration import Attrs
from kpi.base.exception import MissingStaticDataError
from kpi.base.protocol import DeviceProtocol
from kpi.infra.download.devices import download_device_df
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.util import assign_var


class DeviceSchema(FieldRegistry[DeviceProtocol]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        device_type_ids = set().union(
            *(self.get(field).device_type_ids() for field in self.plan)
        )
        device_df = download_device_df(
            dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
            list(device_type_ids),
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
