from collections import defaultdict
from datetime import date
from typing import Annotated, Any, cast
from uuid import UUID

from core.database import get_db
from core.db_query import OutputType
from core.models import Project as DBProject
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, interfaces, utils
from app._crud.operational.kpi_instances import (
    get_kpi_instances as crud_get_kpi_instances,
)
from app._crud.operational.projects import create_project as crud_create_project
from app._crud.operational.report_instances import (
    get_report_instances as crud_get_report_instances,
)
from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed
from app.logger import logger
from core import enumerations, models

DESCRIPTION_404 = "Project not found"

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[interfaces.Project], operation_id="get_projects")
async def get_projects(
    *,
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    project_ids_excluded: Annotated[list[UUID] | None, Query()] = None,
    project_type_ids: Annotated[list[int] | None, Query()] = None,
    project_status_type_ids: Annotated[
        list[enumerations.ProjectStatusType] | None, Query()
    ] = None,
    name_short: str | None = None,
    name_shorts: Annotated[list[str] | None, Query()] = None,
    name_long: str | None = None,
    has_pv_pcs_modules: bool | None = None,
    kpi_instance_kpi_type_ids: Annotated[list[int] | None, Query()] = None,
    report_instance_report_type_ids: Annotated[list[int] | None, Query()] = None,
    db: Session = Depends(get_db),
    user_data: UserAuthed = Depends(get_user),
):
    # Get project IDs permitted for the user
    """todo

    Args:
        project_ids: Description for project_ids.
        project_ids_excluded: Description for project_ids_excluded.
        project_type_ids: Description for project_type_ids.
        project_status_type_ids: Description for project_status_type_ids.
        name_short: Description for name_short.
        name_shorts: Description for name_shorts.
        name_long: Description for name_long.
        has_pv_pcs_modules: Description for has_pv_pcs_modules.
        kpi_instance_kpi_type_ids: Description for kpi_instance_kpi_type_ids.
        report_instance_report_type_ids: Description for
            report_instance_report_type_ids.
        db: Description for db.
        user_data: Description for user_data.
    """
    project_ids_permitted = user_data.operational_project_ids

    # Filter requested project IDs by permitted project IDs
    if project_ids is None:
        project_ids_requested = project_ids_permitted
    else:
        project_ids_requested = list(set(project_ids) & set(project_ids_permitted))

    # Remove excluded project IDs from requested project IDs
    if project_ids_excluded:
        project_ids_requested = list(
            set(project_ids_requested) - set(project_ids_excluded),
        )

    # If report_instance_report_type_ids are requested, filter project IDs that have all
    # requested report_instance_ids
    if report_instance_report_type_ids:
        query = crud_get_report_instances(
            project_ids=project_ids_requested,
            report_type_ids=report_instance_report_type_ids,
            is_visible=None,
        )

        report_instances_df = await query.get_async(output_type=OutputType.POLARS)

        project_id_to_report_type_ids = defaultdict(list)
        for report_instance in report_instances_df.to_dicts():
            project_id_to_report_type_ids[report_instance["project_id"]].append(
                report_instance["report_type_id"],
            )

        # Identify project_ids that have all requested report_instance_report_type_ids
        project_ids_report_instances = [
            project_id
            for project_id in project_id_to_report_type_ids
            if all(
                report_type_id in project_id_to_report_type_ids.get(project_id, [])
                for report_type_id in report_instance_report_type_ids
            )
        ]

        project_ids_requested = list(
            set(project_ids_requested) & set(project_ids_report_instances),
        )

    # If kpi_instance_kpi_type_ids are requested, filter project IDs that have all
    # requested kpi_instance_ids
    if kpi_instance_kpi_type_ids:
        kpi_instances = crud_get_kpi_instances(
            db=db,
            project_ids=project_ids_requested,
            kpi_type_ids=kpi_instance_kpi_type_ids,
            is_visible=None,
        )

        project_id_to_kpi_type_ids = defaultdict(list)
        for kpi_instance in kpi_instances:
            project_id_to_kpi_type_ids[kpi_instance.project_id].append(
                kpi_instance.kpi_type_id,
            )

        # Identify project_ids that have all requested kpi_instance_kpi_type_ids
        project_ids_kpi_instances = [
            project_id
            for project_id in project_id_to_kpi_type_ids
            if all(
                kpi_type_id in project_id_to_kpi_type_ids.get(project_id, [])
                for kpi_type_id in kpi_instance_kpi_type_ids
            )
        ]

        project_ids_requested = list(
            set(project_ids_requested) & set(project_ids_kpi_instances),
        )

    projects_query = core.crud.operational.projects.get_projects(
        project_ids=project_ids_requested,
        project_type_ids=project_type_ids,
        project_status_type_ids=project_status_type_ids,
        name_short=name_short,
        name_long=name_long,
        name_shorts=name_shorts,
        has_pv_pcs_modules=has_pv_pcs_modules,
    )
    projects_df = await projects_query.get_async(
        output_type=OutputType.POLARS,
    )
    projects_dicts: list[dict[str, Any]] = projects_df.to_dicts()

    if user_data.public_metadata.get("demo"):
        # Cast to satisfy mypy's invariance requirements
        projects_for_anon = cast(list[models.Project | dict[str, Any]], projects_dicts)
        projects_anonymized = utils.anonymize_projects(projects=projects_for_anon)
        # Cast back to list of dicts since we know they're all dicts in this path
        projects_dicts = cast(list[dict[str, Any]], projects_anonymized)

    # Sort projects by name_short
    projects_dicts.sort(key=lambda project: project["name_short"])

    return projects_dicts


@router.get(
    "/{project_id}",
    response_model=interfaces.Project,
    dependencies=[Depends(dependencies.check_project_access_async)],
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_project_by_id",
)
async def get_project(
    project_id: UUID,
    user_data: UserAuthed = Depends(get_user),
):
    """todo

    Args:
        project_id: Description for project_id.
        user_data: Description for user_data.
    """
    project_query = core.crud.operational.projects.get_project(
        project_id=project_id,
    )
    project_db_model = await project_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    utils.check_404(value=project_db_model, detail=DESCRIPTION_404)

    if user_data.public_metadata.get("demo"):
        # Runtime check to satisfy type checker
        if project_db_model is None:
            raise ValueError("Project model should not be None after 404 check")
        projects_for_anon = cast(
            list[models.Project | dict[str, Any]], [project_db_model]
        )
        anonymized = utils.anonymize_projects(projects=projects_for_anon)
        # Return the anonymized model directly
        return cast(interfaces.Project, anonymized[0])

    # Return the db model directly (FastAPI will serialize it)
    return cast(interfaces.Project, project_db_model)


@router.post("", response_model=interfaces.Project)
async def create_project(
    project_in: interfaces.ProjectCreate,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: UserAuthed = Depends(get_user),
):
    """Create a new project.

    Args:
        project_in: Description for project_in.
        db: Description for db.
        user_data: Description for user_data.
    """
    db_project = await crud_create_project(
        db=db,
        project_in=project_in,
        user_id=user_data.user_id,
        company_id=user_data.company_id,
    )

    return db_project


@router.put(
    "/{project_id}",
    response_model=interfaces.Project,
    dependencies=[
        Depends(dependencies.check_project_access_async),
        Depends(dependencies.requires_admin_async),
    ],
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="update_project",
)
async def update_project(
    project_id: UUID,
    project_update: interfaces.ProjectUpdate,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Update an existing project.
        Only company admins and super admins can update projects.

    Args:
        project_id: Description for project_id.
        project_update: Description for project_update.
        db: Description for db.
    """
    # Fetch the existing project using AsyncSession
    result = await db.execute(
        select(DBProject).where(DBProject.project_id == project_id)
    )
    existing_project = result.scalar_one_or_none()
    if existing_project is None:
        raise HTTPException(status_code=404, detail=DESCRIPTION_404)

    # Update the project with new data
    update_data = project_update.model_dump(exclude_unset=True)

    # Convert date strings to date objects for SQLAlchemy
    date_fields = {
        "cod",
        "commencement_of_construction_date",
        "financial_close_date",
        "notice_to_proceed_date",
        "mechanical_completion_date",
        "substantial_completion_date",
        "interconnection_approval_date",
        "performance_test_completion_date",
        "placed_in_service_date",
        "first_realtime_data_received_date",
        "first_data_backfilled_date",
    }

    try:
        for field, value in update_data.items():
            # Special-case normalization for PPA JSONB
            if field == "ppa" and value is not None:
                try:
                    if isinstance(value, dict):
                        normalized = {"type": value.get("type", "flat_rate")}
                        if "rate" in value and value["rate"] is not None:
                            normalized["rate"] = float(value["rate"])
                        else:
                            existing_ppa = getattr(existing_project, "ppa", None) or {}
                            if (
                                "rate" in existing_ppa
                                and existing_ppa["rate"] is not None
                            ):
                                normalized["rate"] = float(existing_ppa["rate"])
                        setattr(existing_project, field, normalized)
                        continue
                except Exception as e:
                    logger.warning(
                        f"Failed to process PPA data for project {project_id}: {e}"
                    )
                    # Continue with the next field if PPA processing fails
            if field in date_fields and value is not None:
                # Convert ISO date string to date object
                if isinstance(value, str):
                    parsed_date = date.fromisoformat(value)
                    setattr(existing_project, field, parsed_date)
                    # print(
                    #     f"[DEBUG] Project {project_id} - set {field} = "
                    #     f"{parsed_date} (from string {value})"
                    # )
                else:
                    setattr(existing_project, field, value)
                    # print(f"[DEBUG] Project {project_id} - set {field} = {value}")
            else:
                setattr(existing_project, field, value)

        # Add the object to the session to ensure it's tracked
        db.add(existing_project)

        # Commit the transaction
        await db.commit()
        # print(f"[DEBUG] Project {project_id} update - commit successful")

        # Refresh to get the latest state from the database
        await db.refresh(existing_project)

        # Log values after refresh
        after_refresh_values = {}
        for field in update_data.keys():
            after_refresh_values[field] = getattr(existing_project, field, None)
        # print(
        #     f"[DEBUG] Project {project_id} update - after refresh values: "
        #     f"{after_refresh_values}"
        # )

        return interfaces.Project.model_validate(existing_project)

    except Exception as e:
        # Rollback the transaction on error
        await db.rollback()
        # print(f"[DEBUG] Project {project_id} update - ERROR: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update project: {str(e)}"
        )
