from typing import Self, overload

import xarray as xr
from kpi.base.protocol import SchemaProtocol
from kpi.op.observer import observe
from kpi.op.plan import PipelinePlan


class Schema:
    value: SchemaProtocol

    def __init__(self, value: SchemaProtocol) -> None:
        self.value = value
        self._name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...

    @overload
    def __get__(self, instance: object, owner: type) -> SchemaProtocol: ...

    def __get__(self, instance: object | None, owner: type) -> SchemaProtocol | Self:
        if instance is None:
            return self

        return self.value


class PipelineSchema:
    map: dict[str, SchemaProtocol]

    def __init__(self) -> None:
        mapping = {}
        for base in reversed(type(self).__mro__):
            for name, schema in base.__dict__.items():
                if isinstance(schema, Schema):
                    mapping[name] = schema.value

        self.map = mapping

    def run(self, dataset: xr.Dataset, plan: PipelinePlan) -> xr.Dataset:
        for schema_name, sub_plan in plan.root.items():
            with observe():
                dataset = self.map[schema_name].run(dataset=dataset, plan=sub_plan)
        return dataset

    def full_plan(self) -> PipelinePlan:
        return PipelinePlan(
            {name: schema.full_plan() for name, schema in self.map.items()}
        )
