from fastapi import APIRouter, Depends

from app.dependencies import check_project_access_async
from app.v1.operational.project import (
    project_cmms_tickets,
    project_contracts,
    project_data,
    project_data_last_updated,
    project_devices,
    project_documents,
    project_drone_inspections,
    project_equipment_analysis,
    project_events,
    project_kpi_data,
    project_mccarthy_quality,
    project_pg_data_types,
    project_qc,
    project_report_instances,
    project_reports,
    project_status,
    project_tags,
    project_waterfall,
)

router = APIRouter(dependencies=[Depends(check_project_access_async)])
router.include_router(project_contracts.router)
router.include_router(project_data.router)
router.include_router(project_data_last_updated.router)
router.include_router(project_devices.router)
router.include_router(project_events.router)
router.include_router(project_kpi_data.router)
router.include_router(project_reports.router)
router.include_router(project_report_instances.router)
router.include_router(project_tags.router)
router.include_router(project_status.router)
router.include_router(project_mccarthy_quality.router)
router.include_router(project_documents.router)
router.include_router(project_equipment_analysis.router)
router.include_router(project_pg_data_types.router)
router.include_router(project_pg_data_types.deprecated_router)
router.include_router(project_cmms_tickets.router)
router.include_router(project_qc.router)
router.include_router(project_waterfall.router)
router.include_router(project_drone_inspections.router)
