from abc import ABC, abstractmethod

import xarray as xr
from kpi.base.protocol import NodeProtocol, schema_protocol
from kpi.op.plan import MultiFieldPlan, SingleFieldPlan


@schema_protocol
class SchemaAbstract[T: NodeProtocol](ABC):
    map: dict[str, T]

    @abstractmethod
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        pass

    def full_plan(self) -> MultiFieldPlan:
        return MultiFieldPlan(
            fields=[
                SingleFieldPlan(
                    field_name=name,
                    inputs={input: False for input in value.inputs()},
                )
                for name, value in self.map.items()
            ]
        )
