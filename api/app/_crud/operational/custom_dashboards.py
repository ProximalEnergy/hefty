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
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
        project_id: TODO: describe.
    """
    query = (
        select(models.CustomDashboard)
        .filter(models.CustomDashboard.owner_user_id == user_id)
        .filter(models.CustomDashboard.project_id == project_id)
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
    """todo

    Args:
        db: TODO: describe.
        owner_user_id: TODO: describe.
        project_id: TODO: describe.
        dashboard_name: TODO: describe.
        default_time_range: TODO: describe.
        default_kpi_time_range: TODO: describe.
        components: TODO: describe.
    """
    new_uuid = uuid.uuid4()

    # Create dashboard components and add them individually
    db_dashboard_components = []
    for component in components:
        db_component = models.CustomDashboardComponent(
            component_type=enumerations.ComponentType[
                component.component_type.upper()
            ].value,
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
    """todo

    Args:
        db: TODO: describe.
        dashboard_id: TODO: describe.
        owner_user_id: TODO: describe.
        project_id: TODO: describe.
        dashboard_name: TODO: describe.
        default_time_range: TODO: describe.
        default_kpi_time_range: TODO: describe.
        components: TODO: describe.
    """
    query = (
        select(models.CustomDashboard)
        .filter(models.CustomDashboard.dashboard_id == dashboard_id)
        .filter(models.CustomDashboard.owner_user_id == owner_user_id)
        .filter(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    existing_dashboard = result.scalar_one_or_none()

    if not existing_dashboard:
        raise ValueError("Dashboard not found or access denied")

    # Delete existing components for this dashboard
    # First, get all component IDs from the dashboard's components list
    existing_component_ids = [
        comp["component_id"] for comp in existing_dashboard.components
    ]

    if existing_component_ids:
        delete_query = delete(models.CustomDashboardComponent).where(
            models.CustomDashboardComponent.component_id.in_(existing_component_ids)
        )
        await db.execute(delete_query)

    # Create new dashboard components
    db_dashboard_components = []
    for component in components:
        db_component = models.CustomDashboardComponent(
            component_type=enumerations.ComponentType[
                component.component_type.upper()
            ].value,
            config=component.config,
        )
        db.add(db_component)
        db_dashboard_components.append(db_component)

    # Commit component changes
    await db.commit()

    # Refresh individual objects to get the component_id
    for component in db_dashboard_components:
        await db.refresh(component)

    # Create component sizing data
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

    # Update the dashboard
    existing_dashboard.dashboard_name = dashboard_name
    existing_dashboard.default_time_range = default_time_range
    existing_dashboard.default_kpi_time_range = default_kpi_time_range
    # Update components using the model's update method if available, or direct assignment
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
    """Get a single dashboard by ID with all its components.

    Args:
        db: TODO: describe.
        dashboard_id: TODO: describe.
        user_id: TODO: describe.
        project_id: TODO: describe.
    """
    # First get the dashboard
    query = (
        select(models.CustomDashboard)
        .filter(models.CustomDashboard.dashboard_id == dashboard_id)
        .filter(models.CustomDashboard.owner_user_id == user_id)
        .filter(models.CustomDashboard.project_id == project_id)
    )
    result = await db.execute(query)
    dashboard = result.scalar_one_or_none()

    if not dashboard:
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
        db: TODO: describe.
        dashboard_id: TODO: describe.
        owner_user_id: TODO: describe.
        project_id: TODO: describe.
    """
    # First, get the existing dashboard to verify ownership
    query = (
        select(models.CustomDashboard)
        .filter(models.CustomDashboard.dashboard_id == dashboard_id)
        .filter(models.CustomDashboard.owner_user_id == owner_user_id)
        .filter(models.CustomDashboard.project_id == project_id)
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
