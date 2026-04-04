import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.util import assign_var


class CalcSchema(FieldRegistry[CalcProtocol]):
    plan: dict[str, set[str]]

    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        for field_name, to_delete in self.plan.items():
            with observe(field_name=field_name):
                assign_var(
                    dataset,
                    field_name,
                    self.get(field_name).run(dataset=dataset),
                )
            dataset = dataset.drop_vars(to_delete, errors="ignore")
        return dataset
