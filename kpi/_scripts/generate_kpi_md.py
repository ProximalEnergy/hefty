from pathlib import Path

from core.db_query import DbQuery
from core.enumerations import KPITypeEnum, OutputType
from core import models
from kpi.doc.reference import doc_link_field_ref
from kpi.registry.upload.api import UPLOAD
from pydantic import BaseModel
from sqlalchemy import select

OUTPUT_PATH = Path("docs/generated/kpi_type_metadata.md")

kpi_type_ids = [model.kpi_type.value for model in UPLOAD.values()]


class KPITypeMetadata(BaseModel):
    kpi_type: KPITypeEnum
    name_long: str
    description: str | None
    unit: str | None
    version: str
    project_var_link: str
    device_var_link: str | None
    scale: float | None
    offset: float | None


def render_kpi_markdown(*, metadata: KPITypeMetadata) -> str:
    device_var_link = metadata.device_var_link or ""
    description = metadata.description or ""
    unit = metadata.unit or ""

    return "\n".join(
        [
            f"### {metadata.name_long}",
            description,
            "",
            "| Parameter | Value |",
            "| --- | --- |",
            f"| KPI Type ID | {metadata.kpi_type.value} |",
            f"| Unit | {unit} |",
            f"| Version | {metadata.version} |",
            f"| Project Variable | {metadata.project_var_link} |",
            f"| Device Variable | {device_var_link} |",
        ]
    )


def render_markdown_page(*, metadata_list: list[KPITypeMetadata]) -> str:
    header = "\n".join(
        [
            "# Daily KPIs",
            "",
            "This page outlines the end result of the pipeline resulting in daily "
            "summary metrics at the project level and on a per-device basis.",
        ]
    )
    sections = [
        render_kpi_markdown(metadata=metadata)
        for metadata in metadata_list
    ]
    return "\n\n".join([header, *sections]) + "\n"


statement = (
    select(
        models.KPIType.kpi_type_id,
        models.KPIType.name_short,
        models.KPIType.name_long,
        models.KPIType.description,
        models.KPIType.unit,
    )
    .where(models.KPIType.kpi_type_id.in_(kpi_type_ids))
    .order_by(models.KPIType.kpi_type_id)
)

result = DbQuery(query=statement).get(output_type=OutputType.POLARS)

metadata_list = []
for row in result.to_dicts():
    kpi_type = KPITypeEnum(row["kpi_type_id"])
    upload_model = UPLOAD[kpi_type.name]
    metadata = KPITypeMetadata(
        kpi_type=kpi_type,
        name_long=row["name_long"],
        description=row["description"],
        unit=row["unit"],
        version=upload_model.version,
        project_var_link=doc_link_field_ref(upload_model.project_var),
        device_var_link=(
            doc_link_field_ref(upload_model.device_var)
            if upload_model.device_var is not None
            else None
        ),
        scale=upload_model.scale,
        offset=upload_model.offset,
    )
    metadata_list.append(metadata)

OUTPUT_PATH.write_text(render_markdown_page(metadata_list=metadata_list))