from uuid import UUID

from core.enumerations import ProjectStatusType
from core.models import Project as DBProject
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app._crud.admin.user_projects import deep_delete_project
from app.dependencies import get_async_db, requires_superadmin_async
from app.logger import logger

router = APIRouter()


# ///////////////

# THIS FUNCTION IS COMMENTED OUT FOR SAFETY PURPOSES


# ///////////////
@router.delete("/{project_id}", dependencies=[Depends(requires_superadmin_async)])
async def delete_project_deep(
    project_id: UUID,
    confirm: bool = Query(
        False,
        description="Must be set to true to confirm the irreversible deletion "
        "of the project and all related data",
    ),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Deep delete a project and all related data.

        **WARNING: This operation is irreversible and will permanently delete:**
        - The project itself
        - All user assignments to the project
        - All user subscriptions for the project
        - All company associations with the project
        - All permissions related to the project
        - All documents associated with the project
        - All contracts for the project
        - All KPI alerts, instances, and data
        - All timeseries data
        - All report instances
        - Project metadata and last updated records

        **Requirements:**
        - Must be a superadmin user
        - Must set `confirm=true` query parameter to proceed

        **Returns:**
        - Success message if deletion completed
        - 404 if project not found
        - 400 if confirmation not provided
        - 403 if not authorized (not superadmin)

    Args:
        project_id: TODO: describe.
        confirm: TODO: describe.
        db: TODO: describe.
    """
    raise HTTPException(status_code=499, detail="This operation is banned")
    try:
        # Validate confirmation parameter
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Confirmation required",
                    "message": "Deep deletion requires explicit confirmation. "
                    "Set confirm=true to proceed.",
                    "project_id": str(project_id),
                },
            )

        logger.warning(
            f"Superadmin initiated deep deletion request for project "
            f"{project_id} with confirmation"
        )

        # First, get the project to check its status
        project = (
            await db.scalars(
                select(DBProject).where(DBProject.project_id == project_id)
            )
        ).first()

        if not project:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Project not found",
                    "message": f"Project with ID {project_id} does not exist",
                    "project_id": str(project_id),
                },
            )

        # Check if project status is ONBOARDING before allowing deletion
        if project.project_status_type_id != ProjectStatusType.ONBOARDING.value:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid project status",
                    "message": f"Project deletion is only allowed for projects with "
                    f"ONBOARDING status. Current status ID: "
                    f"{project.project_status_type_id}",
                    "project_id": str(project_id),
                    "current_status_id": project.project_status_type_id,
                    "required_status_id": ProjectStatusType.ONBOARDING.value,
                },
            )

        logger.warning(
            f"Project {project_id} has ONBOARDING status, proceeding with deletion"
        )

        # Perform the deep deletion
        deleted = await deep_delete_project(
            db=db, project_id=project_id, confirm_deletion=True
        )

        logger.warning(f"Deletion status: {deleted}")

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Project not found",
                    "message": f"Project with ID {project_id} does not exist",
                    "project_id": str(project_id),
                },
            )

        logger.warning(f"Successfully completed deep deletion of project {project_id}")

        return {
            "success": True,
            "message": f"Project {project_id} and all related data have been "
            f"permanently deleted",
            "project_id": str(project_id),
            "warning": "This operation was irreversible",
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Handle validation errors from the CRUD function
        logger.error(f"Validation error during project deletion: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": str(e),
                "project_id": str(project_id),
            },
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            f"Unexpected error during deep deletion of project {project_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred during project deletion",
                "project_id": str(project_id),
            },
        )
