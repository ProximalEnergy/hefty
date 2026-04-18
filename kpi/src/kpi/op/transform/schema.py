import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.op.observer import observe
from kpi.op.plan import FieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var


class CalcSchema(SchemaAbstract[CalcProtocol]):
    def run(self, dataset: xr.Dataset, plan: FieldPlan) -> xr.Dataset:
        for field_name, inputs in plan.root.items():
            with observe(field_name=field_name):
                assign_var(
                    dataset,
                    field_name,
                    self.map[field_name].run(dataset=dataset),
                )
            dataset = dataset.drop_vars(inputs.drop_vars(), errors="ignore")
        return dataset
