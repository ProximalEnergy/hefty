from fastapi import APIRouter, Depends

from app._dependencies import authorization
from app.v1.operational.project import (
    project_calendar,
    project_claims,
    project_cmms_permissions,
    project_cmms_tickets,
    project_contracts,
    project_data,
    project_data_last_updated,
    project_data_timeseries_last,
    project_devices,
    project_documents,
    project_drone_inspections,
    project_event_message_reactions,
    project_event_messages,
    project_events,
    project_gis_combiner,
    project_kpi_data,
    project_kpi_types,
    project_om_contractors,
    project_pv_budgeted,
    project_pv_expected,
    project_qc,
    project_report_instances,
    project_reports,
    project_solar,
    project_status,
    project_tags,
    project_user_project_labels,
    project_waterfall,
)

router = APIRouter(
    prefix="/projects/{project_id}",
    dependencies=[Depends(authorization.require_user_project)],
)
router.include_router(project_calendar.router)
router.include_router(project_claims.router)
router.include_router(project_cmms_permissions.router)
router.include_router(project_cmms_tickets.router)
router.include_router(project_contracts.router)
router.include_router(project_data.router)
router.include_router(project_data_last_updated.router)
router.include_router(project_data_timeseries_last.router)
router.include_router(project_devices.router)
router.include_router(project_documents.router)
router.include_router(project_drone_inspections.router)
router.include_router(project_event_message_reactions.router)
router.include_router(project_event_messages.router)
router.include_router(project_events.router)
router.include_router(project_gis_combiner.router)
router.include_router(project_kpi_data.router)
router.include_router(project_kpi_types.router)
router.include_router(project_om_contractors.router)
router.include_router(project_pv_budgeted.router)
router.include_router(project_pv_expected.router)
router.include_router(project_qc.router)
router.include_router(project_report_instances.router)
router.include_router(project_reports.router)
router.include_router(project_solar.router)
router.include_router(project_status.router)
router.include_router(project_tags.router)
router.include_router(project_user_project_labels.router)
router.include_router(project_waterfall.router)
