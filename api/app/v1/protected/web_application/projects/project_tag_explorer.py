import urllib.parse
from typing import Annotated, Any, cast

import pandas as pd
from core.crud.project import tags as crud_project_tags
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

import app.interfaces
from app import dependencies
from app._crud.projects import tags as crud_tags
from app.logger import logger
from core import models


def create_tag_pattern(*, name_scada: str) -> str:
    """Crate a tag pattern from a name_scada string.

    Args:
        name_scada: TODO: describe.
    """
    result = []
    i = 0
    while i < len(name_scada):
        if name_scada[i].isdigit():
            # Found start of digit sequence
            result.append("[INT]")
            # Skip all consecutive digits
            while i < len(name_scada) and name_scada[i].isdigit():
                i += 1
        else:
            result.append(name_scada[i])
            i += 1
    return "".join(result)


def _process_numeric_values(*, values: list) -> tuple[bool, str, int]:
    """Process a list of values to determine if they're numeric and get statistics.
        Returns (is_numeric, value_range, total_unique_values)

    Args:
        values: TODO: describe.
    """
    total_unique_values = len(set(v for v in values if v is not None and pd.notna(v)))

    if not values:
        return False, "N/A", total_unique_values

    try:
        numeric_values = [float(v) for v in values if v is not None and pd.notna(v)]
        is_numeric = len(numeric_values) > 0

        if is_numeric:
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            value_range = f"{min_val:.2f} to {max_val:.2f}"
        else:
            value_range = "N/A"

        return is_numeric, value_range, total_unique_values
    except (ValueError, TypeError):
        return False, "N/A", total_unique_values


# Remove the custom function - we'll use the existing useGetTimeSeries hook instead


router = APIRouter(prefix="/project-tag-explorer", tags=["project_tag_explorer"])


@router.get(
    "/unique-tag-types",
    response_model=list[dict],
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def get_unique_tag_types(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """Get unique tag types for the current project.
        This endpoint is only accessible to superadmins.

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
    """

    try:
        # Read only from the precomputed table in the project schema
        table_rows = (
            project_db.execute(select(models.UniqueTagPatterns)).scalars().all()
        )
        if not table_rows:
            return []

        # Build a single batch lookup for representative tags to avoid N queries
        # Use the first example tag id for each row if available
        pattern_to_sample_id: dict[str, int] = {}
        for row in table_rows:
            try:
                ids: list[int] = []
                if isinstance(row.example_tag_ids, dict):
                    if "tag_ids" in row.example_tag_ids:
                        ids = row.example_tag_ids.get("tag_ids", [])
                    else:
                        vals = list(row.example_tag_ids.values())
                        ids = vals[0] if vals else []
                elif isinstance(row.example_tag_ids, list):
                    ids = row.example_tag_ids
                if ids:
                    pattern_to_sample_id[row.pattern] = ids[0]
            except Exception:
                continue

        sample_ids = list(set(pattern_to_sample_id.values()))
        id_to_tag: dict[int, models.Tag] = {}
        if sample_ids:
            tag_query = select(models.Tag).where(models.Tag.tag_id.in_(sample_ids))
            tags = project_db.execute(tag_query).scalars().all()
            id_to_tag = {t.tag_id: t for t in tags}

        results: list[dict[str, Any]] = []
        for row in table_rows:
            sample_tag_id = pattern_to_sample_id.get(row.pattern)
            sample_tag = id_to_tag.get(sample_tag_id) if sample_tag_id else None

            representative_sensor_type_id = (
                (sample_tag.sensor_type_id or 0) if sample_tag else 0
            )
            representative_unit_scale = sample_tag.unit_scale if sample_tag else None
            representative_unit_offset = sample_tag.unit_offset if sample_tag else None
            representative_unit_scada = sample_tag.unit_scada if sample_tag else None

            results.append(
                {
                    "project_id": str(project.project_id),
                    "project_name": project.name_long,
                    "project_name_short": project.name_short,
                    "sensor_type_id": representative_sensor_type_id,
                    "scada_type": None,
                    "unit_scada": representative_unit_scada,
                    "unit_offset": representative_unit_offset,
                    "unit_scale": representative_unit_scale,
                    "tag_pattern": row.pattern,
                    "count": row.count,
                    "examples": [],
                    "sample_tag_id": sample_tag_id,
                }
            )

        results.sort(key=lambda x: cast(int, x["count"]), reverse=True)
        return results

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing project: {str(e)}"
        )


class AssignPatternSensorTypeRequest(BaseModel):
    """todo"""

    project_id: str
    tag_pattern: str
    sensor_type_id: int
    unit_scale: float | None
    unit_offset: float | None
    unit_scada: str | None


@router.post(
    "/assign-pattern-sensor-type",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def assign_sensor_type_to_pattern(
    request: AssignPatternSensorTypeRequest,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    db: Annotated[Session, Depends(get_db)],
):
    # Get sensor type
    """todo

    Args:
        request: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        db: TODO: describe.
    """
    try:
        # First, check if any tags match the pattern (for validation)
        sample_tags = crud_tags.get_sample_tags_by_pattern_digits_only(
            project_db=project_db, pattern=request.tag_pattern, limit=1
        )

        if not sample_tags:
            raise HTTPException(
                status_code=404, detail="No tags found matching this pattern"
            )

        # Use bulk update for better performance
        updated_count = crud_tags.update_tags_sensor_type_by_pattern_bulk(
            project_db=project_db,
            pattern=request.tag_pattern,
            sensor_type_id=request.sensor_type_id,
            unit_scale=request.unit_scale,
            unit_offset=request.unit_offset,
            unit_scada=request.unit_scada,
        )

        # Update project spec with current used_sensor_type_ids
        # Get all unique sensor type IDs from tags in this project
        unique_sensor_type_ids = crud_project_tags.get_unique_sensor_type_ids_from_tags(
            db=project_db
        )

        # Update the project spec in the operational database
        # We need to use the main database session for this, not the project database
        stmt = (
            update(models.Project)
            .where(models.Project.project_id == project.project_id)
            .values(
                spec=models.Project.spec.op("||")(
                    {"used_sensor_type_ids": unique_sensor_type_ids}
                )
            )
        )
        db.execute(stmt)
        db.commit()

        return {
            "message": f"Successfully updated {updated_count} tags",
            "updated_count": updated_count,
            "pattern": request.tag_pattern,
            "sensor_type_id": request.sensor_type_id,
            "unit_scale": request.unit_scale,
            "unit_offset": request.unit_offset,
            "unit_scada": request.unit_scada,
            "updated_spec": {"used_sensor_type_ids": unique_sensor_type_ids},
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error assigning sensor type to pattern: {str(e)}"
        )


@router.put(
    "/unique-tag-patterns",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
    status_code=201,
)
async def put_unique_tag_patterns(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[app.interfaces.Project, Depends(dependencies.get_project_api)],
):
    """todo

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
    """
    try:
        tags_query = crud_project_tags.get_project_tags_v2(
            include_ghost_tags=True,
        )
        tags_df = await tags_query.get_async(
            output_type=OutputType.PANDAS,
            schema=project.name_short,
        )

        # Group by tag pattern
        patterns: dict[str, dict] = {}
        for _, tag in tags_df.iterrows():
            name_scada = tag["name_scada"]
            if not name_scada:
                continue
            pattern = create_tag_pattern(name_scada=str(name_scada))

            # If pattern is not in patterns, initialize it
            if pattern not in patterns:
                patterns[pattern] = {
                    "pattern": pattern,
                    "count": 0,
                    "example_tag_ids": [],
                }

            # Increment count
            patterns[pattern]["count"] += 1

            # Add the tag_id to the example_tag_ids list
            patterns[pattern]["example_tag_ids"].append(int(tag["tag_id"]))

        # Convert to list and sort by count
        unique_patterns = list(patterns.values())
        unique_patterns.sort(key=lambda x: x["count"], reverse=True)

        # Remove existing rows
        project_db.execute(delete(models.UniqueTagPatterns))

        # Prepare rows for bulk insert
        rows = [
            models.UniqueTagPatterns(
                pattern=item["pattern"],
                count=int(item["count"]),
                # Store as dict per models.py definition, with single tag_id
                example_tag_ids={"tag_ids": [item["example_tag_ids"][0]]},
            )
            for item in unique_patterns
        ]

        # Bulk insert rows
        project_db.bulk_save_objects(rows)
        project_db.commit()

    except Exception as e:
        # Rollback DB transaction if anything failed during write
        project_db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error populating unique tag patterns: {str(e)}",
        )


@router.get(
    "/tag-pattern-samples/{tag_pattern:path}",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def get_tag_pattern_samples(
    tag_pattern: str,
    start: str | None = None,
    end: str | None = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """Get sample values for all tags in a specific pattern.
        Returns up to 10 random tags from the pattern with their sample values.

    Args:
        tag_pattern: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    try:
        # URL decode the tag pattern
        tag_pattern = urllib.parse.unquote(tag_pattern)

        # Get sample tags that match this pattern using CRUD function
        sample_tags = crud_tags.get_sample_tags_by_pattern_digits_only(
            project_db=project_db, pattern=tag_pattern, limit=5
        )

        # Parse start and end dates, or use default 1 day if not provided
        # (reduced for performance)
        if start and end:
            start_date = pd.Timestamp(start)
            end_date = pd.Timestamp(end)
        else:
            end_date = pd.Timestamp.utcnow()
            start_date = end_date - pd.Timedelta(days=1)

        # For each tag, get sample values from the timeseries data
        tag_samples = []
        for tag in sample_tags:
            try:
                data_timeseries_instance = await DataTimeseries(
                    project_name_short=project.name_short,
                    filter_method=FilterMethod.TAG_IDS,
                    filter_values=[tag.tag_id],
                    query_start=start_date,
                    query_end=end_date,
                    project_db=project_db,
                    apply_scale_and_offset=False,
                ).get()

                df = data_timeseries_instance.df.to_pandas()
                df = df.set_index("time")
                df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
                df.columns = df.columns.astype(int)

                # Process the DataFrame data
                values = []
                timestamps = []

                if not df.empty and tag.tag_id in df.columns:
                    # Get non-null values and their corresponding timestamps
                    non_null_data = df[tag.tag_id].dropna()

                    values = non_null_data.tolist()
                    timestamps = non_null_data.index.tz_convert(
                        project.time_zone
                    ).tolist()

                is_numeric, value_range, total_unique_values = _process_numeric_values(
                    values=values
                )
            except Exception as e:
                # Continue with empty data
                # Log error for debugging but don't fail the request

                logger.warning(
                    f"Error getting timeseries data for tag {tag.tag_id}: {e}"
                )

            tag_samples.append(
                {
                    "tag_name": tag.name_scada,
                    "tag_id": tag.tag_id,
                    "sample_values": values,  # Show all returned data
                    "timestamps": timestamps,  # Show all timestamps
                    "is_numeric": is_numeric,
                    "value_range": value_range,
                    "total_unique_values": total_unique_values,
                }
            )

        return {
            "tag_pattern": tag_pattern,
            "sample_tags": tag_samples,
            "total_sample_tags": len(tag_samples),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting tag pattern samples: {str(e)}"
        )


@router.get(
    "/tag-pattern-tags/{tag_pattern:path}",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def get_tag_pattern_tags(
    tag_pattern: str,
    project_db: Session = Depends(dependencies.get_project_db),
):
    """Fetch all tags that match a given tag pattern (with [INT] wildcards).
        Returns lightweight tag info for client-side processing.

    Args:
        tag_pattern: TODO: describe.
        project_db: TODO: describe.
    """
    try:
        decoded_pattern = urllib.parse.unquote(tag_pattern)
        tags = crud_tags.get_tags_by_pattern_digits_only(
            project_db=project_db, pattern=decoded_pattern
        )

        return [
            {
                "tag_id": t.tag_id,
                "name_scada": t.name_scada,
                "name_short": t.name_short,
                "device_id": t.device_id,
                "sensor_type_id": t.sensor_type_id,
            }
            for t in tags
            if t.name_scada is not None
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting tags for pattern: {str(e)}"
        )
