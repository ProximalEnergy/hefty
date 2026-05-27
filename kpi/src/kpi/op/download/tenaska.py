from typing import Literal

import xarray as xr
from kpi.base.context import get_context
from kpi.base.protocol import schema_protocol
from kpi.domain.util import scale_offset
from kpi.infra.download.tenaska import (
    data_array_from_elements,
    download_tenaska_data,
    time_array_from_data,
)
from kpi.op.field import Field
from kpi.op.node import NodeModel, node_type
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var
from pydantic import BaseModel


@node_type
class TenaskaModel(NodeModel):
    kind: Literal["TenaskaModel"] = "TenaskaModel"
    column_name: str
    scale: float | None
    offset: float | None


def tenaska_field(
    column_name: str, scale: float | None = None, offset: float | None = None
) -> Field[TenaskaModel]:
    return Field[TenaskaModel](
        TenaskaModel(
            column_name=column_name,
            scale=scale,
            offset=offset,
        )
    )


@schema_protocol
class TenaskaSchema(BaseModel, SchemaAbstract[TenaskaModel]):
    kind: Literal["TenaskaSchema"] = "TenaskaSchema"

    map: dict[str, TenaskaModel]
    url: str

    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)

        tenaska_data = download_tenaska_data(
            project_id=context.project_id,
            start_tz_aware=context.start_tz_aware,
            end_tz_aware=context.end_tz_aware,
            url=self.url,
        )

        time = time_array_from_data(data=tenaska_data)
        elements = tenaska_data["Elements"]

        for field_name in plan.outputs():
            with observe(field_name=field_name):
                model = self.map[field_name]
                value = data_array_from_elements(
                    elements=elements,
                    column_name=model.column_name,
                    time=time,
                )
                assign_var(
                    dataset,
                    field_name,
                    scale_offset(value, scale=model.scale, offset=model.offset),
                )

        return dataset
