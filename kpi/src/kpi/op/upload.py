import warnings

import xarray as xr
from core.enumerations import KPITypeEnum
from kpi.base.context import get_context
from kpi.base.protocol import NodeProtocol, node_protocol, schema_protocol
from kpi.domain.util import scale_offset
from kpi.infra.util import get_project_by_id
from kpi.infra.write_kpi import (
    arrays_to_rows,
    get_application_name,
    insert_device_kpi_data_bulk,
)
from kpi.infra.write_kpi import (
    kpi_get_kpi_instances as get_kpi_instances,
)
from kpi.op.download.util import MarkdownDocModel
from kpi.op.field import Field
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import select_optional, select_var
from pydantic import ConfigDict


@node_protocol
class UploadModel(MarkdownDocModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    kpi_type: KPITypeEnum
    version: str
    project_var: Field[NodeProtocol]
    device_var: Field[NodeProtocol] | None = None
    scale: float | None = None
    offset: float | None = None

    def inputs(self) -> set[str]:
        return (
            {self.project_var.name, self.device_var.name}
            if self.device_var is not None
            else {self.project_var.name}
        )


def merge_upload_maps_strict(
    *, maps: list[dict[str, UploadModel]]
) -> dict[str, UploadModel]:
    merged: dict[str, UploadModel] = {}
    for mapping in maps:
        overlap = merged.keys() & mapping.keys()
        if overlap:
            msg = f"Duplicate upload keys: {sorted(overlap)}"
            raise ValueError(msg)
        merged.update(mapping)
    return merged


@schema_protocol
class UploadSchema(SchemaAbstract[UploadModel]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)

        project = get_project_by_id(project_id=context.project_id)
        kpi_type_ids = get_kpi_instances(project_id=project.project_id)

        data_rows = []

        for field_plan in plan.fields:
            with observe(field_name=field_plan.field_name):
                model = self.map[field_plan.field_name]
                if model.kpi_type.value not in kpi_type_ids:
                    warnings.warn(
                        message=(
                            f"KPI {repr(model.kpi_type)} has no instance for project "
                            f"{project.name_short}"
                        )
                    )
                    continue
                device_data = None
                if model.device_var is not None:
                    device_data = select_optional(dataset, model.device_var.name)
                    if device_data is not None:
                        device_data = scale_offset(
                            device_data, scale=model.scale, offset=model.offset
                        )
                data_rows.extend(
                    arrays_to_rows(
                        project_data=scale_offset(
                            select_var(dataset, model.project_var.name),
                            scale=model.scale,
                            offset=model.offset,
                        ),
                        device_data=device_data,
                        version=model.version,
                        project_id=project.project_id,
                        kpi_type=model.kpi_type,
                        start=context.start_date,
                        end=context.end_date,
                    )
                )
            dataset = dataset.drop_vars(field_plan.to_delete(), errors="ignore")

        insert_device_kpi_data_bulk(
            application_name=get_application_name(),
            data_rows=data_rows,
        )
        return dataset
