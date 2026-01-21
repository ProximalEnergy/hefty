from fastapi import APIRouter

from app import utils
from app.v1.protected.web_application.projects import project_tag_explorer
from app.v1.protected.web_application.projects.battery_settlement import (
    battery_settlement,
)
from app.v1.protected.web_application.projects.combiner_correlation_analysis import (
    combiner_correlation_analysis,
)
from app.v1.protected.web_application.projects.custom_dash import custom_dash
from app.v1.protected.web_application.projects.device_details import device_details
from app.v1.protected.web_application.projects.equipment_analysis import (
    equipment_analysis,
)
from app.v1.protected.web_application.projects.events import events
from app.v1.protected.web_application.projects.real_time import real_time
from app.v1.protected.web_application.projects.reports import reports

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["projects"],
    include_in_schema=utils.get_include_in_schema(),
)

router.include_router(equipment_analysis.router)
router.include_router(device_details.router)
router.include_router(project_tag_explorer.router)
router.include_router(real_time.router)
router.include_router(events.router)
router.include_router(custom_dash.router)
router.include_router(battery_settlement.router)
router.include_router(combiner_correlation_analysis.router)
router.include_router(reports.router)
