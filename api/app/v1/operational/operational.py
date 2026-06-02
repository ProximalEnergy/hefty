from fastapi import APIRouter, Depends

from app._dependencies.authentication import get_user
from app.v1.operational import (
    aws,
    bess_strings,
    cec_pv_modules,
    contract_categories,
    device_models,
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
    user_project_labels,
)
from app.v1.operational.project import project

router = APIRouter(
    prefix="/operational",
    tags=["operational"],
    dependencies=[Depends(get_user)],
)
router.include_router(aws.router)
router.include_router(bess_strings.router)
router.include_router(cec_pv_modules.router)
router.include_router(contract_categories.router)
router.include_router(device_models.router)
router.include_router(device_types.router)
router.include_router(drone_integrations.router)
router.include_router(drone_permissions.router)
router.include_router(drone_providers.router)
router.include_router(failure_modes.router)
router.include_router(kpi_data.router)
router.include_router(kpi_instances.router)
router.include_router(kpi_types.router)
router.include_router(project.router)
router.include_router(project_data_last_updated.router)
router.include_router(project_types.router)
router.include_router(projects.router)
router.include_router(pv_budgeted_data.router)
router.include_router(pv_inverters.router)
router.include_router(pv_modules.router)
router.include_router(pv_rackings.router)
router.include_router(report_instances.router)
router.include_router(report_types.router)
router.include_router(root_causes.router)
router.include_router(sensor_types.router)
router.include_router(user_project_labels.router)
