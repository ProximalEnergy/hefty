from abc import ABC, abstractmethod

import xarray as xr
from kpi.base.protocol import NodeProtocol
from kpi.op.plan import MultiFieldPlan, SingleFieldPlan


class SchemaAbstract[T: NodeProtocol](ABC):
    def __init__(self, map: dict[str, T]) -> None:
        self.map = map

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
