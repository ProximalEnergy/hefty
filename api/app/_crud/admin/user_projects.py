import uuid
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import logger
from core import models


async def get_users_with_project_access(
    *,
    db: AsyncSession,
    company_id: UUID,
    project_id: UUID,
) -> list[models.User]:
    """Get users from a company with access to a project"""
    query = (
        select(models.User)
        .join(models.UserProject, models.User.user_id == models.UserProject.user_id)
        .where(models.User.company_id == company_id)
        .where(models.UserProject.operational_project_id == project_id)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def assign_project_to_user(
    *,
    db: AsyncSession,
    user_id: str,
    project_id: UUID,
) -> models.UserProject:
    """Assign a project to a user"""
    try:
        # Check if the assignment already exists
        query = select(models.UserProject).where(
            models.UserProject.user_id == user_id,
            models.UserProject.operational_project_id == project_id,
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Project {project_id} already assigned to user {user_id}")
            return existing

        # Create new assignment
        user_project = models.UserProject(
            user_id=user_id,
            operational_project_id=project_id,
        )

        db.add(user_project)
        await db.commit()
        await db.refresh(user_project)

        logger.info(f"Successfully assigned project {project_id} to user {user_id}")
        return user_project

    except Exception as e:
        logger.error(f"Failed to assign project {project_id} to user {user_id}: {e}")
        await db.rollback()
        raise


async def assign_project_to_relevant_users(
    *,
    db: AsyncSession,
    creator_user_id: str,
    creator_company_id: UUID,
    project_id: UUID,
    do_commit: bool = True,
) -> None:
    """
    Assign a project to:
    1. The user who created it
    2. All admins (user_type_id = 2) in the creator's company
    3. All superadmins (user_type_id = 1) regardless of company

    Args:
        do_commit: Whether to commit the transaction. Defaults to True.
                  Set to False for atomic operations where commit is handled externally.
    """
    try:
        # Get all users who should have access to this project
        users_query = select(models.User).where(
            # Creator
            (models.User.user_id == creator_user_id)
            |
            # Company admins
            (
                (models.User.company_id == creator_company_id)
                & (models.User.user_type_id == 2)
            )
            |
            # All superadmins
            (models.User.user_type_id == 1)
        )
        users_result = await db.execute(users_query)
        users_to_assign = users_result.scalars().all()

        # Get existing assignments to avoid duplicates
        existing_query = select(models.UserProject.user_id).where(
            models.UserProject.operational_project_id == project_id
        )
        existing_result = await db.execute(existing_query)
        existing_user_ids = {
            assignment for assignment in existing_result.scalars().all()
        }

        # Create new assignments
        new_assignments = []
        for user in users_to_assign:
            if user.user_id not in existing_user_ids:
                new_assignments.append(
                    models.UserProject(
                        user_id=user.user_id,
                        operational_project_id=project_id,
                    )
                )

        if new_assignments:
            db.add_all(new_assignments)
            if do_commit:
                await db.commit()

            assigned_user_ids = [assignment.user_id for assignment in new_assignments]
            logger.info(
                f"{'Successfully assigned' if do_commit else 'Prepared assignment of'} "
                f"project {project_id} to users: "
                f"{assigned_user_ids}"
            )
        else:
            logger.info(f"No new assignments needed for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to assign project {project_id} to relevant users: {e}")
        if do_commit:
            await db.rollback()
        raise


async def update_user_project_favorite(
    *,
    db: AsyncSession,
    user_id: str,
    project_id: UUID,
    is_favorited: bool,
) -> models.UserProject:
    """Update the is_favorited field for a user's project"""
    try:
        # Find the existing user project relationship
        query = select(models.UserProject).where(
            models.UserProject.user_id == user_id,
            models.UserProject.operational_project_id == project_id,
        )
        result = await db.execute(query)
        user_project = result.scalar_one_or_none()

        if not user_project:
            raise ValueError(
                f"User {user_id} does not have access to project {project_id}"
            )

        # Update the is_favorited field
        user_project.is_favorited = is_favorited

        await db.commit()
        await db.refresh(user_project)

        logger.info(
            f"Successfully updated favorite status for user "
            f"{user_id}, project {project_id} to {is_favorited}"
        )
        return user_project

    except Exception as e:
        logger.error(
            f"Failed to update favorite status for user "
            f"{user_id}, project {project_id}: {e}"
        )
        await db.rollback()
        raise


async def update_user_projects(
    *,
    db: AsyncSession,
    user_ids: list[str],
    operational_project_ids: list[list[uuid.UUID]],
):
    """Update user project assignments for multiple users"""
    # Delete existing entries for these users
    delete_stmt = delete(models.UserProject).where(
        models.UserProject.user_id.in_(user_ids)
    )
    await db.execute(delete_stmt)

    # Create new entries
    new_entries = []
    for user_id, project_ids in zip(user_ids, operational_project_ids):
        for project_id in project_ids:
            new_entries.append(
                models.UserProject(
                    user_id=user_id,
                    operational_project_id=project_id,
                ),
            )

    # Bulk insert all new entries
    if new_entries:
        db.add_all(new_entries)

    await db.commit()


# ///////////////

# THIS FUNCTION IS COMMENTED OUT FOR SAFETY PURPOSES


# ///////////////
async def deep_delete_project(
    *,
    db: AsyncSession,
    project_id: UUID,
    confirm_deletion: bool = False,
) -> bool:
    """
    Deep delete a project by removing all related records from tables that reference it:
    1. Admin tables: user_projects, user_subscriptions, company_projects,
    company_permissions, user_permissions
    2. Operational tables: documents, contracts, kpi_alerts, kpi_instances,
    data_timeseries, kpi_data, project_data_last_updated, report_instances, cmms_devices
    3. Finally the project itself from operational.projects

    WARNING: This operation is irreversible and will permanently delete all data related
    to the project.

    Args:
        db: The SQLAlchemy database session
        project_id: The UUID of the project to delete
        confirm_deletion: Safety parameter that must be True to proceed with deletion

    Returns:
        True if deletion was successful, False if project was not found

    Raises:
        ValueError: If confirm_deletion is not True
        Exception: If the deletion fails
    """
    # raise ValueError("THIS OPERATION IS BANNED")
    # Safety check to prevent accidental deletions
    if not confirm_deletion:
        raise ValueError(
            "Deep deletion requires explicit confirmation. Set confirm_deletion=True to"
            " proceed."
        )

    try:
        # First, check if the project exists
        query = select(models.Project).where(models.Project.project_id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            logger.warning(f"Project {project_id} not found for deletion")
            return False

        logger.warning(
            f"Starting deep deletion of project {project_id} ({project.name_long}). "
            f"This operation is irreversible."
        )

        deletion_counts = {}

        # Delete from admin schema tables
        # user_projects
        delete_stmt = delete(models.UserProject).where(
            models.UserProject.operational_project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["user_projects"] = result.rowcount

        # user_subscriptions
        delete_stmt = delete(models.UserSubscription).where(
            models.UserSubscription.operational_project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["user_subscriptions"] = result.rowcount

        # company_projects
        delete_stmt = delete(models.CompanyProject).where(
            models.CompanyProject.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["company_projects"] = result.rowcount

        # company_permissions
        delete_stmt = delete(models.CompanyPermission).where(
            models.CompanyPermission.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["company_permissions"] = result.rowcount

        # user_permissions
        delete_stmt = delete(models.UserPermission).where(
            models.UserPermission.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["user_permissions"] = result.rowcount

        # Delete from operational schema tables
        # documents
        delete_stmt = delete(models.Document).where(
            models.Document.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["documents"] = result.rowcount

        # contracts
        delete_stmt = delete(models.Contract).where(
            models.Contract.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["contracts"] = result.rowcount

        # kpi_alerts (if exists)
        try:
            delete_stmt = delete(models.KPIAlert).where(
                models.KPIAlert.project_id == project_id
            )
            result = await db.execute(delete_stmt)
            result = cast(CursorResult, result)
            deletion_counts["kpi_alerts"] = result.rowcount
        except AttributeError:
            # KPIAlert model might not exist or have different structure
            pass

        # kpi_instances
        delete_stmt = delete(models.KPIInstance).where(
            models.KPIInstance.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["kpi_instances"] = result.rowcount

        # data_timeseries
        delete_stmt = delete(models.OperationalDataTimeseries).where(
            models.OperationalDataTimeseries.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["data_timeseries"] = result.rowcount

        # kpi_data
        delete_stmt = delete(models.OperationalKPIData).where(
            models.OperationalKPIData.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["kpi_data"] = result.rowcount

        # project_data_last_updated
        delete_stmt = delete(models.ProjectDataLastUpdated).where(
            models.ProjectDataLastUpdated.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["project_data_last_updated"] = result.rowcount

        # report_instances
        delete_stmt = delete(models.ReportInstance).where(
            models.ReportInstance.project_id == project_id
        )
        result = await db.execute(delete_stmt)
        result = cast(CursorResult, result)
        deletion_counts["report_instances"] = result.rowcount

        # Note: CMMSDevice doesn't have a direct project_id field
        # It references devices through device_id,
        # which would require a more complex query
        # Skipping CMMSDevice deletion for now as it requires joining with devices table

        # Finally, delete the project itself
        delete_stmt = delete(models.Project).where(
            models.Project.project_id == project_id
        )
        await db.execute(delete_stmt)
        await db.commit()

        # Log the deletion summary
        total_related_records = sum(deletion_counts.values())
        logger.info(
            f"Successfully deep deleted project {project_id}. "
            f"Deleted {total_related_records} related records: {deletion_counts}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to deep delete project {project_id}: {e}")
        await db.rollback()
        raise
