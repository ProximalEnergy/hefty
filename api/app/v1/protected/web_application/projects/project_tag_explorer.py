import re
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import dependencies, utils
from app._crud.projects import tags as crud_tags
from core import models


def create_tag_pattern(*, name_scada: str) -> str:
    """
    Create a pattern from name_scada by replacing integers with [INT].
    Examples:
    - "PowerElectronics Freesun Inverter Temps 1_Temp_IGBT5" -> "PowerElectronics Freesun Inverter Temps [INT]_Temp_IGBT[INT]"
    - "Inverter_1_Power" -> "Inverter_[INT]_Power"
    """
    # Replace sequences of digits with [INT]
    pattern = re.sub(r"\d+", "[INT]", name_scada)
    return pattern


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

    unique_tag_types = []

    try:
        # Get unique tag types using CRUD function
        project_tag_types = crud_tags.get_unique_tag_types(
            project_db=project_db,
            limit=limit,
            include_null_sensor_types=include_null_sensor_types,
            only_null_sensor_types=only_null_sensor_types,
        )

        # Group by pattern to create unique tag types
        pattern_groups = {}

        for tag_type in project_tag_types:
            if tag_type.name_scada:
                pattern = create_tag_pattern(name_scada=tag_type.name_scada)

                if pattern not in pattern_groups:
                    pattern_groups[pattern] = {
                        "project_id": str(project.project_id),
                        "project_name": project.name_long,
                        "project_name_short": project.name_short,
                        "sensor_type_id": tag_type.sensor_type_id,
                        "scada_type": tag_type.scada_type,
                        "unit_scada": tag_type.unit_scada,
                        "unit_offset": tag_type.unit_offset,
                        "unit_scale": tag_type.unit_scale,
                        "tag_pattern": pattern,
                        "count": 0,
                        "examples": [],
                        "sample_tag_id": None,  # Will be set later
                    }

                pattern_groups[pattern]["count"] += tag_type.count
                # Keep track of a few examples for reference
                if len(pattern_groups[pattern]["examples"]) < 3:
                    pattern_groups[pattern]["examples"].append(tag_type.name_scada)

        # Get a sample tag_id for each pattern
        for pattern in pattern_groups:
            sample_tag_id = crud_tags.get_sample_tag_id_by_pattern(
                project_db=project_db, pattern=pattern
            )
            if sample_tag_id:
                pattern_groups[pattern]["sample_tag_id"] = sample_tag_id

        # Convert to list and sort by count
        unique_tag_types = list(pattern_groups.values())
        unique_tag_types.sort(key=lambda x: x["count"], reverse=True)

    except Exception as e:
        # Log error and return empty list
        raise HTTPException(
            status_code=500, detail=f"Error processing project: {str(e)}"
        )

    return unique_tag_types


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
    db: Annotated[Session, Depends(dependencies.get_db)],
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
        # Find all tags that match this pattern using CRUD function
        matching_tags = crud_tags.get_tags_by_pattern(
            project_db=project_db, pattern=request.tag_pattern
        )

        if not matching_tags:
            raise HTTPException(
                status_code=404, detail="No tags found matching this pattern"
            )

        # Update all matching tags using CRUD function
        updated_count = crud_tags.update_tags_sensor_type(
            project_db=project_db,
            tags=matching_tags,
            sensor_type_id=request.sensor_type_id,
            unit_scale=request.unit_scale,
            unit_offset=request.unit_offset,
        )

        return {
            "message": f"Successfully updated {updated_count} tags",
            "updated_count": updated_count,
            "pattern": request.tag_pattern,
            "sensor_type_id": request.sensor_type_id,
            "unit_scale": request.unit_scale,
            "unit_offset": request.unit_offset,
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
        is_numeric = False
        value_range = "N/A"
        total_unique_values = 0

        if not df.empty and tag.tag_id in df.columns:
            values = df[tag.tag_id].dropna().unique().tolist()
            total_unique_values = len(values)

            if values:
                # Determine if values are numeric
                try:
                    numeric_values = [
                        float(v) for v in values if v is not None and pd.notna(v)
                    ]
                    is_numeric = len(numeric_values) > 0

                    if is_numeric:
                        min_val = min(numeric_values)
                        max_val = max(numeric_values)
                        value_range = f"{min_val:.2f} to {max_val:.2f}"
                    else:
                        value_range = "N/A"
                except (ValueError, TypeError):
                    is_numeric = False
                    value_range = "N/A"

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
        import urllib.parse

        tag_pattern = urllib.parse.unquote(tag_pattern)

        # Get sample tags that match this pattern using CRUD function
        sample_tags = crud_tags.get_sample_tags_by_pattern(
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
                sample_tag_ids = [tag.tag_id]

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
                    is_numeric = False
                    value_range = "N/A"
                    total_unique_values = 0

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

                        total_unique_values = len(non_null_data.unique())

                        if values:
                            # Determine if values are numeric
                            try:
                                numeric_values = [
                                    float(v)
                                    for v in values
                                    if v is not None and pd.notna(v)
                                ]
                                is_numeric = len(numeric_values) > 0

                                if is_numeric:
                                    min_val = min(numeric_values)
                                    max_val = max(numeric_values)
                                    value_range = f"{min_val:.2f} to {max_val:.2f}"
                                else:
                                    value_range = "N/A"
                            except (ValueError, TypeError):
                                is_numeric = False
                                value_range = "N/A"
                except Exception as e:
                    # Continue with empty data
                    # Log error for debugging but don't fail the request
                    import logging

                    logging.getLogger(__name__).warning(
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
            except Exception as e:
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
