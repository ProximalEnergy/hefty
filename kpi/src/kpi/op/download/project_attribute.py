import numpy as np
import xarray as xr
from kpi.base.context import get_context
from kpi.base.exception import MissingStaticDataError
from kpi.base.protocol import (
    ProjectAttributeProtocol,
    project_attribute_protocol,
    schema_protocol,
)
from kpi.domain.util import scale_offset
from kpi.infra.util import get_project_by_id
from kpi.op.download.util import NoInputsModel
from kpi.op.field import Field
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var
from shapely import wkb  # type: ignore

from core import models


@project_attribute_protocol
class ProjectAttributeModel(NoInputsModel):
    source_field_name: str
    scale: float | None
    offset: float | None

    def run(self, project: models.Project) -> xr.DataArray:
        return scale_offset(
            xr.DataArray(data=getattr(project, self.source_field_name) or np.nan),
            scale=self.scale,
            offset=self.offset,
        )


def project_attribute_field(
    source_field_name: str,
    scale: float | None = None,
    offset: float | None = None,
) -> Field[ProjectAttributeProtocol]:
    return Field[ProjectAttributeProtocol](
        ProjectAttributeModel(
            source_field_name=source_field_name,
            scale=scale,
            offset=offset,
        )
    )


@schema_protocol
class ProjectAttributeSchema(SchemaAbstract[ProjectAttributeProtocol]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)
        project = get_project_by_id(project_id=context.project_id)
        for field_name in plan.outputs():
            with observe(field_name=field_name):
                model = self.map[field_name]
                assign_var(
                    dataset,
                    field_name,
                    model.run(project=project),
                    exc=MissingStaticDataError,
                )
        return dataset


@project_attribute_protocol
class Latitude:
    def run(self, project: models.Project) -> xr.DataArray:
        geometry = wkb.loads(project.point.desc)  # type: ignore
        latitude = geometry.y
        return xr.DataArray(data=latitude)

    def inputs(self) -> set[str]:
        return set[str]()


@project_attribute_protocol
class Longitude:
    def run(self, project: models.Project) -> xr.DataArray:
        geometry = wkb.loads(project.point.desc)  # type: ignore
        longitude = geometry.x
        return xr.DataArray(data=longitude)

    def inputs(self) -> set[str]:
        return set[str]()
