import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models


async def get_user_dashboards(
    db: AsyncSession,
    *,
    user_id: str,
    project_id: uuid.UUID,
):
    """Return dashboards owned by a user for a specific project.

    Args:
        db: Database session for executing the dashboard lookup.
        user_id: Identifier of the user who owns the dashboards.
        project_id: Project identifier used to scope dashboards.
    """
    query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.owner_user_id == user_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_shared_user_dashboards(
    db: AsyncSession,
    *,
    user_id: str,
    project_id: uuid.UUID,
):
    """Get all shared user dashboards for a project.

    Args:
        db: Database session for executing the shared dashboard query.
        user_id: Identifier of the user receiving shared dashboards.
        project_id: Project identifier used to filter shared dashboards.
    """
    query = (
        select(models.CustomDashboard)
        .join(
            models.CustomDashboardShare,
            models.CustomDashboard.dashboard_id
            == models.CustomDashboardShare.dashboard_id,
        )
        .where(models.CustomDashboardShare.user_id == user_id)
        .where(models.CustomDashboard.project_id == project_id)
        .where(models.CustomDashboard.owner_user_id != user_id)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def create_user_dashboard(
    db: AsyncSession,
    *,
    owner_user_id: str,
    project_id: uuid.UUID,
    dashboard_name: str,
    default_time_range: enumerations.DefaultTimeRange,
    default_kpi_time_range: enumerations.DefaultKPITimeRange,
    components: list,
):
    """Create a dashboard and its components for a project user.

    Args:
        db: Database session used to persist the dashboard and components.
        owner_user_id: Identifier of the user creating the dashboard.
        project_id: Project identifier that owns the dashboard.
        dashboard_name: Display name for the dashboard.
        default_time_range: Default time window for dashboard visualizations.
        default_kpi_time_range: Default time window for KPI components.
        components: Component payloads including layout and configuration.
    """
    new_uuid = uuid.uuid4()

    # Create dashboard components and add them individually
    db_dashboard_components = []
    for component in components:
        db_component = models.CustomDashboardComponent(
            component_type=enumerations.ComponentType[component.component_type.upper()],
            config=component.config,
        )
        db.add(db_component)
        db_dashboard_components.append(db_component)

    # Commit all changes
    await db.commit()

    # Refresh individual objects to get the component_id
    for component in db_dashboard_components:
        await db.refresh(component)

    component_sizing = [
        {
            "component_id": db_dashboard_components[i].component_id,
            "x": components[i].x,
            "y": components[i].y,
            "w": components[i].w,
            "h": components[i].h,
        }
        for i in range(len(components))
    ]

    # Create the dashboard
    db_dashboard = models.CustomDashboard(
        dashboard_id=new_uuid,
        project_id=project_id,
        dashboard_name=dashboard_name,
        owner_user_id=owner_user_id,
        default_time_range=default_time_range,
        default_kpi_time_range=default_kpi_time_range,
        components=component_sizing,
    )
    db.add(db_dashboard)

    # Create a share record for the dashboard creator
    db_share = models.CustomDashboardShare(
        dashboard_id=new_uuid,
        user_id=owner_user_id,
    )
    db.add(db_share)

    # Commit remaining changes and refresh
    await db.commit()
    await db.refresh(db_dashboard)
    return db_dashboard


async def update_user_dashboard(
    db: AsyncSession,
    *,
    dashboard_id: uuid.UUID,
    owner_user_id: str,
    project_id: uuid.UUID,
    dashboard_name: str,
    default_time_range: enumerations.DefaultTimeRange,
    default_kpi_time_range: enumerations.DefaultKPITimeRange,
    components: list,
):
    # First, get the existing dashboard to verify ownership
    """Update a dashboard and its components owned by the requesting user.

    Args:
        db: Database session used to fetch and persist dashboard changes.
        dashboard_id: Identifier of the dashboard to update.
        owner_user_id: Identifier of the dashboard owner performing the update.
        project_id: Project identifier used to scope the dashboard.
        dashboard_name: New display name for the dashboard.
        default_time_range: Updated default range for dashboard visualizations.
        default_kpi_time_range: Updated default range for KPI components.
        components: Component payloads containing layout and config changes.
    """
    query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.dashboard_id == dashboard_id)
        .where(models.CustomDashboard.owner_user_id == owner_user_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    existing_dashboard = result.scalar_one_or_none()

    if not existing_dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Get existing component IDs from the dashboard
    existing_component_ids = {
        comp["component_id"] for comp in existing_dashboard.components
    }

    # Convert incoming component IDs to integers for comparison
    # (component_id can be str or int from frontend, but DB stores as int)
    incoming_component_ids = set()
    for component in components:
        comp_id = component.component_id
        if isinstance(comp_id, str):
            try:
                incoming_component_ids.add(int(comp_id))
            except (ValueError, TypeError):
                # If it's not a valid integer string, treat as new component
                pass
        elif isinstance(comp_id, int):
            incoming_component_ids.add(comp_id)

    # Find components to delete (exist in DB but not in incoming)
    components_to_delete = existing_component_ids - incoming_component_ids
    if components_to_delete:
        delete_query = delete(models.CustomDashboardComponent).where(
            models.CustomDashboardComponent.component_id.in_(components_to_delete)
        )
        await db.execute(delete_query)

    # Process components: update existing or create new
    # Track which input components map to which DB components and their IDs
    component_mapping: list[
        tuple[models.CustomDashboardComponent, int, int | None]
    ] = []  # List of (db_component, input_component_index, component_id) tuples

    for i, component in enumerate(components):
        comp_id = component.component_id
        # Try to convert to int for DB lookup
        comp_id_int = None
        if isinstance(comp_id, str):
            try:
                comp_id_int = int(comp_id)
            except (ValueError, TypeError):
                pass
        elif isinstance(comp_id, int):
            comp_id_int = comp_id

        # Check if this component already exists
        if comp_id_int and comp_id_int in existing_component_ids:
            # Update existing component
            component_query = select(models.CustomDashboardComponent).where(
                models.CustomDashboardComponent.component_id == comp_id_int
            )
            component_result = await db.execute(component_query)
            db_component = component_result.scalar_one_or_none()

            if db_component:
                # Update the existing component
                db_component.component_type = enumerations.ComponentType[
                    component.component_type.upper()
                ]
                db_component.config = component.config
                # Store the component_id we already know (from the query)
                component_mapping.append((db_component, i, comp_id_int))
            else:
                # Component ID was provided but doesn't exist, create new
                new_component = models.CustomDashboardComponent(
                    component_type=enumerations.ComponentType[
                        component.component_type.upper()
                    ],
                    config=component.config,
                )
                db.add(new_component)
                component_mapping.append((new_component, i, None))
        else:
            # Create new component
            new_component = models.CustomDashboardComponent(
                component_type=enumerations.ComponentType[
                    component.component_type.upper()
                ],
                config=component.config,
            )
            db.add(new_component)
            component_mapping.append((new_component, i, None))

    # Commit component changes
    await db.commit()

    # Build component sizing data in the correct order
    component_sizing = []
    for db_component, input_index, known_component_id in component_mapping:
        # Use known_component_id if available, otherwise refresh to get new ID
        if known_component_id is not None:
            component_id = known_component_id
        else:
            # This is a new component, refresh to get the generated ID
            await db.refresh(db_component)
            component_id = db_component.component_id

        input_component = components[input_index]
        component_sizing.append(
            {
                "component_id": component_id,
                "x": input_component.x,
                "y": input_component.y,
                "w": input_component.w,
                "h": input_component.h,
            }
        )

    # Update the dashboard
    existing_dashboard.dashboard_name = dashboard_name
    existing_dashboard.default_time_range = default_time_range
    existing_dashboard.default_kpi_time_range = default_kpi_time_range
    # Update components using the model's update method if available, or direct
    # assignment
    setattr(existing_dashboard, "components", component_sizing)

    # Commit all changes and refresh
    await db.commit()
    await db.refresh(existing_dashboard)
    return existing_dashboard


async def get_dashboard_by_id(
    db: AsyncSession,
    *,
    dashboard_id: uuid.UUID,
    user_id: str,
    project_id: uuid.UUID,
):
    """Get a dashboard with its components if the user owns or has share access.

    Args:
        db: Database session for fetching dashboards and components.
        dashboard_id: Dashboard identifier to retrieve.
        user_id: Requesting user who must own or be shared on the dashboard.
        project_id: Project identifier scoping the dashboard.
    """
    # First get the dashboard
    dashboard_query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.dashboard_id == dashboard_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    dashboard_result = await db.execute(dashboard_query)
    dashboard = dashboard_result.scalar_one_or_none()

    if not dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Check if user is the owner
    is_owner = dashboard.owner_user_id == user_id

    # Check if user has access via share (if not owner)
    has_share_access = False
    if not is_owner:
        share_query = select(models.CustomDashboardShare).where(
            models.CustomDashboardShare.dashboard_id == dashboard_id,
            models.CustomDashboardShare.user_id == user_id,
        )
        share_result = await db.execute(share_query)
        share = share_result.scalar_one_or_none()
        has_share_access = share is not None

    # User must be either owner or have share access
    if not is_owner and not has_share_access:
        raise ValueError("Dashboard not found or access denied")

    # Get the component details from the components table
    component_ids = [comp["component_id"] for comp in dashboard.components]

    if not component_ids:
        # No components, return dashboard with empty components list
        return {
            "dashboard_id": dashboard.dashboard_id,
            "dashboard_name": dashboard.dashboard_name,
            "default_time_range": dashboard.default_time_range,
            "default_kpi_time_range": dashboard.default_kpi_time_range,
            "components": [],
            "is_owner": is_owner,
        }

    # Query the components table for detailed component information
    components_query = select(models.CustomDashboardComponent).where(
        models.CustomDashboardComponent.component_id.in_(component_ids)
    )
    components_result = await db.execute(components_query)
    db_components = components_result.scalars().all()

    # Create a mapping of component_id to component details
    component_map = {comp.component_id: comp for comp in db_components}

    # Build the complete components list with all information
    complete_components = []
    for comp_info in dashboard.components:
        component_id = comp_info["component_id"]
        if component_id in component_map:
            db_component = component_map[component_id]
            complete_components.append(
                {
                    "component_id": component_id,
                    "component_type": enumerations.ComponentType(
                        db_component.component_type
                    ).name.lower(),
                    "x": comp_info["x"],
                    "y": comp_info["y"],
                    "w": comp_info["w"],
                    "h": comp_info["h"],
                    "config": db_component.config,
                }
            )

    return {
        "dashboard_id": dashboard.dashboard_id,
        "dashboard_name": dashboard.dashboard_name,
        "default_time_range": dashboard.default_time_range,
        "default_kpi_time_range": dashboard.default_kpi_time_range,
        "components": complete_components,
        "is_owner": is_owner,
    }


async def delete_user_dashboard(
    db: AsyncSession,
    *,
    dashboard_id: uuid.UUID,
    owner_user_id: str,
    project_id: uuid.UUID,
):
    """Delete a dashboard and all its components.

    Args:
        db: Database session used for dashboard and component deletion.
        dashboard_id: Dashboard identifier targeted for removal.
        owner_user_id: Owner identifier used to verify delete permissions.
        project_id: Project identifier scoping the dashboard.
    """
    # First, get the existing dashboard to verify ownership
    query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.dashboard_id == dashboard_id)
        .where(models.CustomDashboard.owner_user_id == owner_user_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    existing_dashboard = result.scalar_one_or_none()

    if not existing_dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Get all component IDs from the dashboard's components list
    existing_component_ids = [
        comp["component_id"] for comp in existing_dashboard.components
    ]

    # Delete all components for this dashboard
    if existing_component_ids:
        delete_components_query = delete(models.CustomDashboardComponent).where(
            models.CustomDashboardComponent.component_id.in_(existing_component_ids)
        )
        await db.execute(delete_components_query)

    # Delete the dashboard itself
    delete_dashboard_query = delete(models.CustomDashboard).where(
        models.CustomDashboard.dashboard_id == dashboard_id
    )
    await db.execute(delete_dashboard_query)

    # Commit all changes
    await db.commit()

    return {"message": "Dashboard deleted successfully"}


async def get_dashboard_shared_users(
    db: AsyncSession,
    *,
    dashboard_id: uuid.UUID,
    owner_user_id: str,
    project_id: uuid.UUID,
):
    """Get all user IDs who have share access to a dashboard.

    Args:
        db: Database session for retrieving dashboard share records.
        dashboard_id: Dashboard identifier used to find shares.
        owner_user_id: Owner identifier used to validate access.
        project_id: Project identifier scoping the dashboard.
    """
    # First, verify the dashboard exists and user is the owner
    query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.dashboard_id == dashboard_id)
        .where(models.CustomDashboard.owner_user_id == owner_user_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    existing_dashboard = result.scalar_one_or_none()

    if not existing_dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Get all shares for this dashboard
    share_query = select(models.CustomDashboardShare).where(
        models.CustomDashboardShare.dashboard_id == dashboard_id
    )
    share_result = await db.execute(share_query)
    shares = share_result.scalars().all()

    # Return list of user IDs (excluding the owner)
    return [share.user_id for share in shares if share.user_id != owner_user_id]


async def share_user_dashboard(
    db: AsyncSession,
    *,
    dashboard_id: uuid.UUID,
    owner_user_id: str,
    shared_user_id: str,
    project_id: uuid.UUID,
):
    """Share a dashboard with a user.

    Args:
        db: Database session for creating dashboard share records.
        dashboard_id: Dashboard identifier being shared.
        owner_user_id: Owner identifier used to authorize the share.
        shared_user_id: User identifier receiving dashboard access.
        project_id: Project identifier scoping the dashboard.
    """
    # First, get the existing dashboard to verify ownership
    query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.dashboard_id == dashboard_id)
        .where(models.CustomDashboard.owner_user_id == owner_user_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    existing_dashboard = result.scalar_one_or_none()

    if not existing_dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Check if the shared user already has access to the dashboard
    share_query = select(models.CustomDashboardShare).where(
        models.CustomDashboardShare.dashboard_id == dashboard_id,
        models.CustomDashboardShare.user_id == shared_user_id,
    )
    share_result = await db.execute(share_query)
    existing_share = share_result.scalar_one_or_none()

    if existing_share:
        raise ValueError("Dashboard is already shared with this user")

    # Create the share record
    db_share = models.CustomDashboardShare(
        dashboard_id=dashboard_id,
        user_id=shared_user_id,
    )
    db.add(db_share)

    # Commit changes
    await db.commit()
    await db.refresh(db_share)

    return {"message": "Dashboard shared successfully", "share_id": db_share.share_id}


async def unshare_user_dashboard(
    db: AsyncSession,
    *,
    dashboard_id: uuid.UUID,
    owner_user_id: str,
    shared_user_id: str,
    project_id: uuid.UUID,
):
    """Unshare a dashboard with a user.

    Args:
        db: Database session for deleting dashboard share records.
        dashboard_id: Dashboard identifier being unshared.
        owner_user_id: Owner identifier used to authorize the removal.
        shared_user_id: User identifier losing dashboard access.
        project_id: Project identifier scoping the dashboard.
    """
    # First, get the existing dashboard to verify ownership
    query = (
        select(models.CustomDashboard)
        .where(models.CustomDashboard.dashboard_id == dashboard_id)
        .where(models.CustomDashboard.owner_user_id == owner_user_id)
        .where(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    existing_dashboard = result.scalar_one_or_none()

    if not existing_dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Find the share record
    share_query = select(models.CustomDashboardShare).where(
        models.CustomDashboardShare.dashboard_id == dashboard_id,
        models.CustomDashboardShare.user_id == shared_user_id,
    )
    share_result = await db.execute(share_query)
    existing_share = share_result.scalar_one_or_none()

    if not existing_share:
        raise ValueError("Dashboard is not shared with this user")

    # Delete the share record
    delete_query = delete(models.CustomDashboardShare).where(
        models.CustomDashboardShare.dashboard_id == dashboard_id,
        models.CustomDashboardShare.user_id == shared_user_id,
    )
    await db.execute(delete_query)

    # Commit changes
    await db.commit()

    return {"message": "Dashboard unshared successfully"}
