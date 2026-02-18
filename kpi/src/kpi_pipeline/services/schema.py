from typing import Type

import xarray as xr

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import (
    DeviceAttributeModel,
    ExpectedEnergyModel,
    ProjectAttributeModel,
    SensorModel,
    StatusModel,
)
from kpi_pipeline.base.protocols import (
    CalcProtocol,
    DataDownloadModelProtocol,
    Implements,
    SchemaProtocol,
    TransformProtocol,
)
from kpi_pipeline.base.schema import SchemaAbstract, TransformFieldSchemaAbstract
from kpi_pipeline.services.action.transform import (
    DownloadDeviceAttributesTransform,
    DownloadExpectedEnergyTransform,
    DownloadProjectAttributesTransform,
    DownloadStatusTimeSeriesTransform,
    DownloadTimeSeriesTransform,
    DownloadTransformAbstract,
    MergeTransform,
    TransformList,
)

transform_schema_schema = Implements[
    SchemaProtocol[xr.Dataset, SchemaProtocol]
].decorator


@transform_schema_schema
class SchemaListSchema(SchemaAbstract[xr.Dataset, SchemaProtocol]):
    _allowed_attribute_type = SchemaProtocol

    @classmethod
    def _export(cls, scope: str | None = None) -> TransformProtocol:
        base_scope = scope or cls.__name__
        return TransformList(
            steps=[
                schema.export(scope=f"{base_scope}.{name}")
                for name, schema in cls._registry.items()
            ]
        )


@transform_schema_schema
class SchemaMergeSchema(SchemaAbstract[xr.Dataset, SchemaProtocol]):
    _allowed_attribute_type = SchemaProtocol

    @classmethod
    def _export(cls, scope: str | None = None) -> TransformProtocol:
        base_scope = scope or cls.__name__
        return MergeTransform(
            transforms=[
                schema.export(scope=f"{base_scope}.{name}")
                for name, schema in cls._registry.items()
            ]
        )


transform_field_schema = Implements[SchemaProtocol[xr.Dataset, Field]].decorator


@transform_field_schema
class DownloadSchemaAbstract[V](
    TransformFieldSchemaAbstract[DataDownloadModelProtocol]
):
    _transform: Type[DownloadTransformAbstract]
    _allowed_field_value_type: Type[DataDownloadModelProtocol]

    @classmethod
    def _export(cls, scope: str | None = None) -> TransformProtocol:
        return cls._transform(map=cls.value_registry())


@transform_field_schema
class DownloadProjectAttributesSchema(DownloadSchemaAbstract[ProjectAttributeModel]):
    _allowed_field_value_type = ProjectAttributeModel
    _transform = DownloadProjectAttributesTransform


@transform_field_schema
class DownloadDeviceAttributesSchema(DownloadSchemaAbstract[DeviceAttributeModel]):
    _allowed_field_value_type = DeviceAttributeModel
    _transform = DownloadDeviceAttributesTransform


@transform_field_schema
class DownloadTimeSeriesSchema(DownloadSchemaAbstract[SensorModel]):
    _allowed_field_value_type = SensorModel
    _transform = DownloadTimeSeriesTransform


@transform_field_schema
class DownloadExpectedEnergySchema(DownloadSchemaAbstract[ExpectedEnergyModel]):
    _allowed_field_value_type = ExpectedEnergyModel
    _transform = DownloadExpectedEnergyTransform


@transform_field_schema
class DownloadStatusTimeSeriesSchema(DownloadSchemaAbstract[StatusModel]):
    _allowed_field_value_type = StatusModel
    _transform = DownloadStatusTimeSeriesTransform


@transform_field_schema
class AddCalculationsSchema(TransformFieldSchemaAbstract[CalcProtocol]):
    _allowed_field_value_type = CalcProtocol

    @classmethod
    def _export(cls, scope: str | None = None) -> TransformProtocol:
        return TransformList.from_calc_map(
            calc_map=cls.value_registry(),
        )


@transform_field_schema
class NewCalculationsSchema(TransformFieldSchemaAbstract[CalcProtocol]):
    _allowed_field_value_type = CalcProtocol

    @classmethod
    def _export(cls, scope: str | None = None) -> TransformProtocol:
        return MergeTransform.from_calc_map(
            calc_map=cls.value_registry(),
            pass_through=False,
        )
