from typing import Annotated, Literal, Self

import pydantic as pyd
import xarray as xr
from kpi.base.protocol import schema_protocol
from kpi.op.download.api import DownloadSchemaType
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan, PipelinePlan
from kpi.op.transform.schema import CalcSchema
from kpi.op.upload import UploadSchema
from pydantic import BaseModel

SchemaType = DownloadSchemaType | CalcSchema | UploadSchema


@schema_protocol
class PipelineSchema(BaseModel):
    kind: Literal["PipelineSchema"] = "PipelineSchema"
    map: dict[str, Annotated[Self | SchemaType, pyd.Field(discriminator="kind")]]

    def run(self, dataset: xr.Dataset, plan: PipelinePlan) -> xr.Dataset:
        for schema_name in plan.steps.keys():
            dataset = self.run_step(dataset=dataset, plan=plan, step_name=schema_name)
        return dataset

    def run_step(
        self, dataset: xr.Dataset, plan: PipelinePlan, step_name: str
    ) -> xr.Dataset:
        sub_plan = plan.steps[step_name]
        schema = self.map[step_name]
        with observe():
            if isinstance(schema, PipelineSchema):
                if not isinstance(sub_plan, PipelinePlan):
                    raise TypeError("PipelineSchema requires PipelinePlan")
                dataset = schema.run(dataset=dataset, plan=sub_plan)
            else:
                if not isinstance(sub_plan, MultiFieldPlan):
                    raise TypeError("Leaf schema requires MultiFieldPlan")
                dataset = schema.run(dataset=dataset, plan=sub_plan)
        return dataset

    def full_plan(self) -> PipelinePlan:
        return PipelinePlan(
            steps={name: schema.full_plan() for name, schema in self.map.items()}
        )
