import numpy as np
import xarray as xr
from kpi.base.enumeration import Attrs
from kpi.base.exception import MissingStaticDataError
from kpi.base.protocol import ProjectAttributeProtocol
from kpi.domain.util import scale_offset
from kpi.infra.util import get_project_from_database
from kpi.op.field import Field, NoInputs
from kpi.op.field_registry import FieldRegistry
from kpi.op.observer import observe
from kpi.op.util import assign_var
from pydantic import BaseModel
from shapely import wkb  # type: ignore

from core import models


class ProjectAttributeModel(BaseModel, NoInputs):
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
) -> Field[ProjectAttributeModel]:
    return Field[ProjectAttributeModel](
        ProjectAttributeModel(
            source_field_name=source_field_name,
            scale=scale,
            offset=offset,
        )
    )


class ProjectAttributeSchema(FieldRegistry[ProjectAttributeProtocol]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        project = get_project_from_database(
            dataset.attrs[Attrs.PROJECT_NAME_SHORT.value]
        )
        for field_name in self.plan:
            with observe(field_name=field_name):
                model = self.get(field_name)
                assign_var(
                    dataset,
                    field_name,
                    model.run(project=project),
                    exc=MissingStaticDataError,
                )
        return dataset


class Latitude(NoInputs):
    def run(self, project: models.Project) -> xr.DataArray:
        geometry = wkb.loads(project.point.desc)  # type: ignore
        latitude = geometry.y
        return xr.DataArray(data=latitude)


class Longitude(NoInputs):
    def run(self, project: models.Project) -> xr.DataArray:
        geometry = wkb.loads(project.point.desc)  # type: ignore
        longitude = geometry.x
        return xr.DataArray(data=longitude)
