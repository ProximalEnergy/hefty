import time
import urllib.parse
from typing import Annotated, Any, cast

import pandas as pd
from core.crud.operational import projects as crud_projects
from core.crud.project import tags as crud_project_tags
from core.dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import dependencies, utils
from app._crud.projects import tags as crud_tags
from app.logger import logger
from core import models


def create_tag_pattern_fast(*, name_scada: str) -> str:
    """
    Faster version of create_tag_pattern using string operations instead of regex.
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
    """
    Process a list of values to determine if they're numeric and get statistics.
    Returns (is_numeric, value_range, total_unique_values)
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
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    limit: int = 500,
    include_null_sensor_types: bool = False,
    only_null_sensor_types: bool = False,
):
    """
    Get unique tag types for the current project.
    This endpoint is only accessible to superadmins.
    """

    try:
        # Read only from the precomputed table in the project schema
        table_rows = project_db.query(models.UniqueTagPatterns).all()
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
            tags = (
                project_db.query(models.Tag)
                .filter(models.Tag.tag_id.in_(sample_ids))
                .all()
            )
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

            results.append(
                {
                    "project_id": str(project.project_id),
                    "project_name": project.name_long,
                    "project_name_short": project.name_short,
                    "sensor_type_id": representative_sensor_type_id,
                    "scada_type": None,
                    "unit_scada": None,
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


@router.get(
    "/sensor-type-assignments",
    response_model=list[dict],
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def get_sensor_type_assignments(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
):
    """
    Get sensor types and their current assignments for the current project.
    This endpoint is only accessible to superadmins.
    """

    try:
        # Get sensor type assignments using CRUD function
        assignments = crud_tags.get_sensor_type_assignments(project_db=project_db)

        # Add project information to each assignment
        for assignment in assignments:
            assignment.update(
                {
                    "project_id": str(project.project_id),
                    "project_name": project.name_long,
                    "project_name_short": project.name_short,
                }
            )

    except Exception as e:
        # Log error and return empty list
        raise HTTPException(
            status_code=500, detail=f"Error processing project: {str(e)}"
        )

    return assignments


@router.post(
    "/assign-sensor-type",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def assign_sensor_type_to_tag(
    project_id: str,
    tag_name_short: str,
    sensor_type_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Assign a sensor type to a specific tag in a project.
    This endpoint is only accessible to superadmins.
    """

    # Get the project
    project = (
        db.query(models.Project).filter(models.Project.project_id == project_id).first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the sensor type
    sensor_type = (
        db.query(models.SensorType)
        .filter(models.SensorType.sensor_type_id == sensor_type_id)
        .first()
    )
    if not sensor_type:
        raise HTTPException(status_code=404, detail="Sensor type not found")

    try:
        # Get project database session using _with_db
        with dependencies._with_db(schema=project.name_short) as project_db:
            # Find the tag by name_short using CRUD function
            tag = crud_tags.get_tag_by_name_short(
                project_db=project_db, name_short=tag_name_short
            )

            if not tag:
                raise HTTPException(status_code=404, detail="Tag not found")

            # Update the tag's sensor_type_id using CRUD function
            crud_tags.update_tag_sensor_type(
                project_db=project_db, tag=tag, sensor_type_id=sensor_type_id
            )

            return {"message": "Sensor type assigned successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error assigning sensor type: {str(e)}"
        )


class AssignPatternSensorTypeRequest(BaseModel):
    project_id: str
    tag_pattern: str
    sensor_type_id: int
    unit_scale: float | None = None
    unit_offset: float | None = None


@router.post(
    "/assign-pattern-sensor-type",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def assign_sensor_type_to_pattern(
    request: AssignPatternSensorTypeRequest,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Assign a sensor type to all tags matching a pattern in a project.
    This endpoint is only accessible to superadmins.
    """

    # Get the sensor type
    sensor_type = (
        project_db.query(models.SensorType)
        .filter(models.SensorType.sensor_type_id == request.sensor_type_id)
        .first()
    )
    if not sensor_type:
        raise HTTPException(status_code=404, detail="Sensor type not found")

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
        )

        # Update project spec with current used_sensor_type_ids
        # Get all unique sensor type IDs from tags in this project
        unique_sensor_type_ids = crud_project_tags.get_unique_sensor_type_ids_from_tags(
            db=project_db
        )

        # Update the project spec in the operational database
        # We need to use the main database session for this, not the project database
        crud_projects.update_project_spec(
            db=db,
            project_id=project.project_id,
            spec_updates={"used_sensor_type_ids": unique_sensor_type_ids},
        )

        return {
            "message": f"Successfully updated {updated_count} tags",
            "updated_count": updated_count,
            "pattern": request.tag_pattern,
            "sensor_type_id": request.sensor_type_id,
            "unit_scale": request.unit_scale,
            "unit_offset": request.unit_offset,
            "updated_spec": {"used_sensor_type_ids": unique_sensor_type_ids},
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error assigning sensor type to pattern: {str(e)}"
        )


@router.get(
    "/tag-samples/{tag_id}",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def get_tag_samples(
    tag_id: int,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project),
):
    """
    Get sample values for a specific tag by tag_id.
    Returns sample values from the last 3 days of data.
    """
    try:
        # Get the tag by ID using CRUD function
        tag = crud_tags.get_tag_by_id(project_db=project_db, tag_id=tag_id)

        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Get 3 days of data using the existing data_df function
        end = pd.Timestamp.utcnow()
        start = end - pd.Timedelta(days=3)

        # Use the existing data_df function to get timeseries data
        df = utils.data_df(
            project_db=project_db,
            project=project,
            tags=[tag],
            start=start,
            end=end,
            interval="5min",
            agg="instantaneous",
            fillna_zero=False,
            unit_scaled=False,
        )

        # Extract unique values from the DataFrame
        values = []
        if not df.empty and tag.tag_id in df.columns:
            values = df[tag.tag_id].dropna().unique().tolist()

        is_numeric, value_range, total_unique_values = _process_numeric_values(
            values=values
        )

        return {
            "tag_id": tag_id,
            "tag_name": tag.name_scada,
            "sample_values": values[:20],  # Show up to 20 unique values
            "is_numeric": is_numeric,
            "value_range": value_range,
            "total_unique_values": total_unique_values,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting tag samples: {str(e)}"
        )


@router.post(
    "/populate-unique-tag-patterns",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def populate_unique_tag_patterns(
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project),
):
    """
    Populate the UniqueTagPatterns table with all tag patterns for the current
    project. Moves away from parquet output and persists in the database.
    """
    try:
        start_time = time.time()

        # Get all unique tag patterns from the project schema
        all_tag_types = crud_tags.get_unique_tag_types(
            project_db=project_db,
            limit=10000000,
            include_null_sensor_types=True,
        )

        # Group by normalized pattern
        pattern_groups: dict[str, dict] = {}
        for tag_type in all_tag_types:
            if not tag_type.name_scada:
                continue
            pattern = create_tag_pattern_fast(name_scada=tag_type.name_scada)
            if pattern not in pattern_groups:
                pattern_groups[pattern] = {
                    "pattern": pattern,
                    "count": 0,
                    "example_tag_ids": [],
                }
            pattern_groups[pattern]["count"] += tag_type.count
            # Use the example_tag_id from the query result directly
            if (
                tag_type.example_tag_id
                and tag_type.example_tag_id
                not in pattern_groups[pattern]["example_tag_ids"]
            ):
                pattern_groups[pattern]["example_tag_ids"].append(
                    tag_type.example_tag_id
                )

        # Convert to list and sort by count
        unique_patterns = list(pattern_groups.values())
        unique_patterns.sort(key=lambda x: x["count"], reverse=True)

        # Replace parquet persistence with database writes into the PROJECT schema
        # Clear existing rows for this tenant (project schema session)
        project_db.query(models.UniqueTagPatterns).delete()

        # Prepare rows for bulk insert
        rows = []
        for item in unique_patterns:
            # Use the first example tag ID if available, otherwise empty list
            example_tag_id = (
                item["example_tag_ids"][0] if item["example_tag_ids"] else None
            )
            rows.append(
                models.UniqueTagPatterns(
                    pattern=item["pattern"],
                    count=int(item["count"]),
                    # Store as dict per models.py definition, with single tag_id
                    example_tag_ids={"tag_ids": [example_tag_id]}
                    if example_tag_id
                    else {"tag_ids": []},
                )
            )

        if rows:
            project_db.bulk_save_objects(rows)
        project_db.commit()

        total_time = time.time() - start_time
        return {
            "message": (f"Inserted {len(rows)} unique tag patterns into the database"),
            "total_patterns": len(rows),
            "total_tags": sum(x["count"] for x in unique_patterns),
            "project_id": str(project.project_id),
            "elapsed_seconds": round(total_time, 3),
        }

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
    project: models.Project = Depends(dependencies.get_project),
):
    """
    Get sample values for all tags in a specific pattern.
    Returns up to 10 random tags from the pattern with their sample values.
    """
    try:
        # URL decode the tag pattern
        tag_pattern = urllib.parse.unquote(tag_pattern)

        # Get sample tags that match this pattern using CRUD function
        sample_tags = crud_tags.get_sample_tags_by_pattern_digits_only(
            project_db=project_db, pattern=tag_pattern, limit=5
        )

        # For each tag, get sample values from the timeseries data
        tag_samples = []
        for tag in sample_tags:
            try:
                # Parse start and end dates, or use default 1 day if not provided (reduced for performance)
                if start and end:
                    start_date = pd.Timestamp(start)
                    end_date = pd.Timestamp(end)
                else:
                    end_date = pd.Timestamp.utcnow()
                    start_date = end_date - pd.Timedelta(
                        days=1
                    )  # Reduced from 3 days to 1 day

                # Get sample tag IDs for this pattern

                # Use the existing utils.data_df function (same as DataBrowsing page)
                try:
                    df = utils.data_df(
                        project_db=project_db,
                        project=project,
                        tags=[tag],
                        start=start_date,
                        end=end_date,
                        interval="5min",  # Use 5min interval for sample data
                        agg="instantaneous",
                        fillna_zero=False,
                        unit_scaled=False,
                    )

                    # Process the DataFrame data
                    values = []
                    timestamps = []

                    if not df.empty and tag.tag_id in df.columns:
                        # Get non-null values and their corresponding timestamps
                        non_null_data = df[tag.tag_id].dropna()

                        # For timeseries, we want time-ordered data, not just unique values
                        # Sample data points across the time range for better visualization
                        if len(non_null_data) > 100:
                            # For large datasets, sample every nth point to get good coverage
                            step = len(non_null_data) // 100
                            sampled_data = non_null_data.iloc[::step]
                            values = sampled_data.tolist()
                            timestamps = sampled_data.index.tolist()
                        else:
                            # For smaller datasets, use all data
                            values = non_null_data.tolist()
                            timestamps = non_null_data.index.tolist()

                    is_numeric, value_range, total_unique_values = (
                        _process_numeric_values(values=values)
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
            except Exception:
                # Continue with other tags even if one fails
                continue

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
    """
    Fetch all tags that match a given tag pattern (with [INT] wildcards).
    Returns lightweight tag info for client-side processing.
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
