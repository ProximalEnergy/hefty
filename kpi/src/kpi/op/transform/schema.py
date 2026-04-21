import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var


class CalcSchema(SchemaAbstract[CalcProtocol]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        for field_plan in plan.fields:
            with observe(field_name=field_plan.field_name):
                assign_var(
                    dataset,
                    field_plan.field_name,
                    self.map[field_plan.field_name].run(dataset=dataset),
                )
            dataset = dataset.drop_vars(field_plan.to_delete(), errors="ignore")
        return dataset
