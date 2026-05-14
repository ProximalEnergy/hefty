from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl
from async_lru import alru_cache
from core.crud.project.tags import get_project_tags_v2
from core.database import with_db_async
from core.db_query import OutputType
from core.enumerations import ProjectDatabaseProvider
from sqlalchemy import select
from sqlalchemy.orm import load_only

from core import models

QUERY_METADATA_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class ProjectQueryMetadata:
    time_zone: str
    data_cagg_interval: str | None
    project_id_int: int
    database_provider: ProjectDatabaseProvider


@alru_cache(maxsize=256, ttl=QUERY_METADATA_TTL_SECONDS)
async def _get_project_query_metadata_cached(
    *,
    project_name_short: str,
) -> ProjectQueryMetadata:
    """Load and cache project metadata used for timeseries queries.

    Args:
        project_name_short: Project short name to resolve.

    Returns:
        Cached metadata required for project query execution.

    Raises:
        ValueError: If the project does not exist.
    """
    stmt = (
        select(models.Project)
        .options(
            load_only(
                models.Project.time_zone,
                models.Project.data_cagg_interval,
                models.Project.project_id_int,
                models.Project.database_provider,
            )
        )
        .where(models.Project.name_short == project_name_short)
    )

    async with with_db_async(schema=None) as operational_db:
        result = await operational_db.execute(stmt)
        project = result.scalar_one_or_none()

    if project is None:
        raise ValueError(f"Project not found: {project_name_short}")

    return ProjectQueryMetadata(
        time_zone=project.time_zone,
        data_cagg_interval=project.data_cagg_interval,
        project_id_int=project.project_id_int,
        database_provider=project.database_provider,
    )


async def get_project_query_metadata_cached(
    *,
    project_name_short: str,
) -> ProjectQueryMetadata:
    """Return cached project metadata for query execution.

    Args:
        project_name_short: Project short name to resolve.

    Returns:
        Cached metadata required for project query execution.
    """
    return await _get_project_query_metadata_cached(
        project_name_short=project_name_short
    )


@alru_cache(maxsize=256, ttl=QUERY_METADATA_TTL_SECONDS)
async def _get_project_tags_cached(
    *,
    project_name_short: str,
    device_type_ids: tuple[int, ...],
    sensor_type_ids: tuple[int, ...],
    deep: bool,
    include_ghost_tags: bool,
) -> pl.DataFrame:
    """Load and cache project tags for a normalized filter request.

    Args:
        project_name_short: Project short name used as the schema name.
        device_type_ids: Normalized device type IDs to filter.
        sensor_type_ids: Normalized sensor type IDs to filter.
        deep: Whether to include deep project relationships.
        include_ghost_tags: Whether to include ghost tags in the result.

    Returns:
        Cached project tag lookup table.
    """
    return await get_project_tags_v2(
        device_type_ids=list(device_type_ids),
        sensor_type_ids=list(sensor_type_ids),
        deep=deep,
        include_ghost_tags=include_ghost_tags,
    ).get_async(output_type=OutputType.POLARS, schema=project_name_short)


async def get_project_tags_cached(
    *,
    project_name_short: str,
    device_type_ids: Sequence[int] = (),
    sensor_type_ids: Sequence[int] = (),
    deep: bool = False,
    include_ghost_tags: bool = False,
) -> pl.DataFrame:
    """Return cached project tags for the requested filters.

    Args:
        project_name_short: Project short name used as the schema name.
        device_type_ids: Device type IDs to filter.
        sensor_type_ids: Sensor type IDs to filter.
        deep: Whether to include deep project relationships.
        include_ghost_tags: Whether to include ghost tags in the result.

    Returns:
        Copy of the cached project tag lookup table.
    """
    tags = await _get_project_tags_cached(
        project_name_short=project_name_short,
        device_type_ids=tuple(sorted(set(device_type_ids))),
        sensor_type_ids=tuple(sorted(set(sensor_type_ids))),
        deep=deep,
        include_ghost_tags=include_ghost_tags,
    )
    return tags.clone()
