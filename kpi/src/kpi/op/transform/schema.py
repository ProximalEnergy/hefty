from typing import Literal

import xarray as xr
from kpi.base.protocol import schema_protocol
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.transform.method import MethodCalc
from kpi.op.util import assign_var
from pydantic import BaseModel


@schema_protocol
class CalcSchema(BaseModel, SchemaAbstract[MethodCalc]):
    kind: Literal["CalcSchema"] = "CalcSchema"

    map: dict[str, MethodCalc]

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
