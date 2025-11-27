from fastapi import APIRouter, Depends

from app import dependencies
from app.v1.operational import (
    aws,
    calendar,
    cec_pv_inverters,
    cec_pv_modules,
    contract_categories,
    data_types,
    device_types,
    drone_integrations,
    drone_permissions,
    drone_providers,
    failure_modes,
    kpi_data,
    kpi_instances,
    kpi_types,
    project_data_last_updated,
    project_types,
    projects,
    pv_budgeted_data,
    pv_inverters,
    pv_modules,
    pv_rackings,
    report_instances,
    report_types,
    root_causes,
    sensor_types,
    status,
    users,
)
from app.v1.operational.project import (
    event_message_reactions,
    event_messages,
    project,
    project_calendar,
    project_om_contractors,
)

get_user_data_async = [Depends(dependencies.get_user_data_async)]

router = APIRouter(
    prefix="/operational",
    tags=["operational"],
    dependencies=get_user_data_async,
)
router.include_router(aws.router)
router.include_router(calendar.router)
router.include_router(cec_pv_inverters.router)
router.include_router(cec_pv_modules.router)
router.include_router(data_types.router)
router.include_router(data_types.deprecated_router)
router.include_router(device_types.router)
router.include_router(device_types.deprecated_router)
router.include_router(failure_modes.router)
router.include_router(project_types.router)
router.include_router(project_types.deprecated_router)
router.include_router(event_message_reactions.router)
router.include_router(event_messages.router)
router.include_router(event_messages.batch_router)
router.include_router(project.router)
router.include_router(project_calendar.router)
router.include_router(project_om_contractors.router)
router.include_router(projects.router)
router.include_router(kpi_data.router)
router.include_router(kpi_instances.router)
router.include_router(kpi_types.router)
router.include_router(report_types.router)
router.include_router(report_types.deprecated_router)
router.include_router(report_instances.router)
router.include_router(root_causes.router)
router.include_router(sensor_types.router)
router.include_router(sensor_types.deprecated_router)
router.include_router(status.router)
router.include_router(pv_modules.router)
router.include_router(pv_rackings.router)
router.include_router(pv_inverters.router)
router.include_router(pv_budgeted_data.router)
router.include_router(drone_integrations.router)
router.include_router(drone_providers.router)
router.include_router(drone_permissions.router)
router.include_router(project_data_last_updated.router)
router.include_router(users.router)
router.include_router(contract_categories.router)
