from abc import ABC, abstractmethod

import xarray as xr
from kpi.base.protocol import NodeProtocol
from kpi.op.plan import FieldPlan, delete_none


class SchemaAbstract[T: NodeProtocol](ABC):
    def __init__(self, map: dict[str, T]) -> None:
        self.map = map

    @abstractmethod
    def run(self, dataset: xr.Dataset, plan: FieldPlan) -> xr.Dataset:
        pass

    def full_plan(self) -> FieldPlan:
        return FieldPlan(
            {name: delete_none(value.inputs()) for name, value in self.map.items()}
        )
