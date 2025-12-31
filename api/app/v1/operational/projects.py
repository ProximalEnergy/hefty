from collections import defaultdict
from datetime import date
from typing import Annotated
from uuid import UUID

from core.dependencies import get_db
from core.models import Project as DBProject
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import custom_types, dependencies, interfaces, utils
from app._crud.operational.kpi_instances import (
    get_kpi_instances as crud_get_kpi_instances,
)
from app._crud.operational.projects import create_project as crud_create_project
from app._crud.operational.report_instances import (
    get_report_instances as crud_get_report_instances,
)
from app.logger import logger
from core import enumerations

DESCRIPTION_404 = "Project not found"

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[interfaces.Project], operation_id="get_projects")
async def get_projects(
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
    deep: custom_types.AnnotatedDeep = False,
    db: Session = Depends(get_db),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),
):
    # Get project IDs permitted for the user
    """todo

    Args:
        project_ids: TODO: describe.
        project_ids_excluded: TODO: describe.
        project_type_ids: TODO: describe.
        project_status_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_shorts: TODO: describe.
        name_long: TODO: describe.
        has_pv_pcs_modules: TODO: describe.
        kpi_instance_kpi_type_ids: TODO: describe.
        report_instance_report_type_ids: TODO: describe.
        deep: TODO: describe.
        db: TODO: describe.
        db_async: TODO: describe.
        user_data: TODO: describe.
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
        report_instances = await crud_get_report_instances(
            db=db_async,
            project_ids=project_ids_requested,
            report_type_ids=report_instance_report_type_ids,
            is_visible=None,
        )

        project_id_to_report_type_ids = defaultdict(list)
        for report_instance in report_instances:
            project_id_to_report_type_ids[report_instance.project_id].append(
                report_instance.report_type_id,
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

    projects = core.crud.operational.projects.get_projects(
        db=db,
        deep=deep,
        project_ids=project_ids_requested,
        project_type_ids=project_type_ids,
        project_status_type_ids=project_status_type_ids,
        name_short=name_short,
        name_long=name_long,
        name_shorts=name_shorts,
        has_pv_pcs_modules=has_pv_pcs_modules,
    ).models()

    if user_data.public_metadata.get("demo"):
        projects = utils.anonymize_projects(projects=projects)

    # Sort projects by name_short
    projects.sort(key=lambda x: x.name_short)

    return projects


@router.get(
    "/{project_id}",
    response_model=interfaces.Project,
    dependencies=[Depends(dependencies.check_project_access_async)],
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_project_by_id",
)
def get_project(
    project_id: UUID,
    deep: custom_types.AnnotatedDeep = False,
    db: Session = Depends(get_db),
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),
):
    """todo

    Args:
        project_id: TODO: describe.
        deep: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """
    project = core.crud.operational.projects.get_project(
        db=db, project_id=project_id, deep=deep
    ).model()
    utils.check_404(value=project, detail=DESCRIPTION_404)

    if user_data.public_metadata.get("demo"):
        [project] = utils.anonymize_projects(projects=[project])

    return project


@router.post("", response_model=interfaces.Project)
async def create_project(
    project_in: interfaces.ProjectCreate,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),
):
    """Create a new project.

    Args:
        project_in: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
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
        project_id: TODO: describe.
        project_update: TODO: describe.
        db: TODO: describe.
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
                    #     f"[DEBUG] Project {project_id} - set {field} = {parsed_date} (from string {value})"
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
        #     f"[DEBUG] Project {project_id} update - after refresh values: {after_refresh_values}"
        # )

        return interfaces.Project.model_validate(existing_project)

    except Exception as e:
        # Rollback the transaction on error
        await db.rollback()
        # print(f"[DEBUG] Project {project_id} update - ERROR: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update project: {str(e)}"
        )
